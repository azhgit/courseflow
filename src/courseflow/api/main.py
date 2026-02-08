import asyncio
import os
import time
from collections import deque, defaultdict
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from courseflow.config import settings

app = FastAPI(title="CourseFlow RAG API")

# Simple in-memory rate limiter and token tracker
# Not persisted across restarts - sufficient for demo/feature branch

if not hasattr(app.state, "rate_timestamps"):
    app.state.rate_timestamps = deque()
if not hasattr(app.state, "daily_count"):
    app.state.daily_count = defaultdict(int)
if not hasattr(app.state, "token_logs"):
    app.state.token_logs = []

DOCS_PATH = os.path.join(os.getcwd(), "docs")

class QueryRequest(BaseModel):
    query: str
    subject: Optional[str] = None

class QueryResponse(BaseModel):
    success: bool
    data: dict
    metadata: dict
    error: Optional[dict]

async def list_docs() -> List[str]:
    # Return list of file paths under docs/
    if not os.path.isdir(DOCS_PATH):
        return []
    files = []
    for root, _, filenames in os.walk(DOCS_PATH):
        for fn in filenames:
            if fn.endswith(".md") or fn.endswith(".txt"):
                files.append(os.path.join(root, fn))
    return files

async def read_file(path: str) -> str:
    return await asyncio.to_thread(lambda: open(path, "r", encoding="utf-8").read())

async def simple_search(query: str, subject: Optional[str], top_k: int = 3):
    # Naive keyword overlap search for demo purposes
    q_tokens = set([t.lower() for t in query.split() if len(t) > 2])
    docs = await list_docs()
    scores = []
    for p in docs:
        if subject and f"/{subject}/" not in p:
            continue
        text = await read_file(p)
        words = set([t.lower().strip(".,!?()[]") for t in text.split() if len(t) > 2])
        overlap = len(q_tokens & words)
        scores.append((overlap, p, text))
    scores.sort(reverse=True, key=lambda x: x[0])
    results = []
    for overlap, p, text in scores[:top_k]:
        # take first 2 paragraphs as snippet
        snippet = "\n\n".join([s.strip() for s in text.split("\n\n") if s.strip()][:2])
        results.append({"source": os.path.relpath(p, DOCS_PATH), "score": overlap, "snippet": snippet})
    return results

def now_ts() -> float:
    return time.time()

def record_token_usage(request_id: str, tokens: int, model: str = "gemini-1.5-flash"):
    app.state.token_logs.append({
        "request_id": request_id,
        "tokens": tokens,
        "model": model,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })
    # update daily count
    day = datetime.utcnow().date().isoformat()
    app.state.daily_count[day] += 1

def check_rate_limit():
    # clean timestamps older than 60s
    now = now_ts()
    while app.state.rate_timestamps and now - app.state.rate_timestamps[0] > 60:
        app.state.rate_timestamps.popleft()
    if len(app.state.rate_timestamps) >= settings.RATE_LIMIT_RPM:
        return False
    # daily
    day = datetime.utcnow().date().isoformat()
    if app.state.daily_count[day] >= settings.RATE_LIMIT_DAILY:
        return False
    return True

def consume_rate_slot():
    app.state.rate_timestamps.append(now_ts())
    day = datetime.utcnow().date().isoformat()
    app.state.daily_count[day] += 1

@app.post("/api/v1/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    # Single-turn only: ignore any conversation history
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="query field is required")

    if not check_rate_limit():
        raise HTTPException(status_code=429, detail={"error": "quota_exceeded", "message": "Gemini API quota exceeded (15 RPM). Retry later.", "retry_after": 60})

    consume_rate_slot()

    # Simple retrieval
    results = await simple_search(req.query, req.subject, top_k=settings.RAG_TOP_K)

    # Build a simple answer using top snippet(s)
    if results:
        top = results[0]
        answer = f"Based on the knowledge base (source: {top['source']}):\n\n{top['snippet']}"
        sources = [r["source"] for r in results]
    else:
        answer = "No relevant documents found in the knowledge base."
        sources = []

    # Approximate token count (words ~= tokens)
    token_count = max(1, len(req.query.split()) + len(answer.split()))
    request_id = f"req_{int(time.time()*1000)}"
    record_token_usage(request_id, token_count)

    metadata = {
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "latency_ms": 0,  # left as 0 for simple demo; infra should measure
        "token_count": token_count,
    }

    return QueryResponse(success=True, data={"answer": answer, "sources": sources, "retrieval_count": len(results)}, metadata=metadata, error=None)

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
