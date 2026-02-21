# CourseFlow RAG API 使用範例

本文檔展示如何使用 CourseFlow RAG API 的各種功能。

## 目錄
- [啟動服務](#啟動服務)
- [健康檢查](#健康檢查)
- [問答查詢](#問答查詢)
- [使用測試腳本](#使用測試腳本)
- [常見錯誤處理](#常見錯誤處理)

---

## 啟動服務

### 方法 1: 使用啟動腳本（推薦）

```bash
# 激活虛擬環境
source .venv/bin/activate

# 使用默認端口 8000
./scripts/start.sh

# 或指定端口
./scripts/start.sh 9000
```

### 方法 2: 手動啟動

```bash
source .venv/bin/activate
uvicorn src.courseflow.api.main:app --host 127.0.0.1 --port 8000 --reload
```

**成功啟動後會看到：**
```
Starting up CourseFlow RAG system...
ChromaDB persist dir: /path/to/data/chroma
Rate limit: 15 RPM
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 健康檢查

檢查所有服務（ChromaDB、SQLite、Rate Limiter）的狀態。

### cURL

```bash
curl http://localhost:8000/api/v1/health
```

### Python

```python
import requests

response = requests.get("http://localhost:8000/api/v1/health")
print(response.json())
```

### 響應範例

```json
{
  "status": "ok",
  "services": {
    "chromadb": {
      "status": "ok",
      "document_count": 17
    },
    "sqlite": {
      "status": "ok",
      "queries_last_24h": 5
    },
    "rate_limit": {
      "status": "ok",
      "requests_in_last_minute": 2,
      "max_requests_per_minute": 15,
      "available_requests": 13
    }
  }
}
```

---

## 問答查詢

### 範例 1: 生物學問題

**請求：**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is photosynthesis?"
  }'
```

**響應：**
```json
{
  "data": {
    "query_id": "uuid-here",
    "answer": "Photosynthesis is the process by which green plants, algae, and some bacteria convert light energy into chemical energy...",
    "sources": [
      {
        "content": "# Photosynthesis: The Process...",
        "source": "docs/biology/photosynthesis.md",
        "subject": "biology",
        "similarity_score": 0.718
      }
    ]
  },
  "metadata": {
    "latency_ms": 1213,
    "timestamp": "2026-02-11T17:55:00Z",
    "token_usage": {
      "prompt_tokens": 2687,
      "completion_tokens": 76,
      "total_tokens": 2763
    }
  }
}
```

### 範例 2: 編程問題

**Python 範例：**
```python
import requests

def ask_question(question: str, base_url: str = "http://localhost:8000"):
    response = requests.post(
        f"{base_url}/api/v1/query",
        json={"query": question},
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# 使用
result = ask_question("How do async functions work in Python?")
print(f"Answer: {result['data']['answer']}")
print(f"Sources: {len(result['data']['sources'])}")
print(f"Latency: {result['metadata']['latency_ms']}ms")
```

### 範例 3: 數學問題

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are derivatives in calculus?"
  }'
```

### 範例 4: 歷史問題

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What caused World War II?"
  }'
```

### 範例 5: 無關問題（測試回退行為）

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the weather today?"
  }'
```

**響應（無相關文檔）：**
```json
{
  "data": {
    "query_id": "uuid-here",
    "answer": "No relevant information found in knowledge base. Please try rephrasing your question.",
    "sources": []
  },
  "metadata": {
    "latency_ms": 0,
    "timestamp": "2026-02-11T17:55:00Z",
    "no_relevant_documents": {
      "threshold": 0.5,
      "max_similarity": 0.23
    }
  }
}
```

---

## 使用測試腳本

我們提供了一個完整的測試腳本來驗證所有功能。

```bash
# 使用默認端口 8000
python scripts/test_api.py

# 使用自定義端口
python scripts/test_api.py 9000
```

**測試內容：**
1. ✅ 健康檢查
2. ✅ 生物學問題
3. ✅ 編程問題
4. ✅ 數學問題
5. ✅ 歷史問題
6. ✅ 無關問題處理

---

## 常見錯誤處理

### 錯誤 1: `{"detail": "Not Found"}`

**原因：** 訪問了不存在的端點（如根路徑 `/`）

**解決方案：** 使用正確的端點
- `/api/v1/health` - 健康檢查
- `/api/v1/query` - 問答
- `/docs` - API 文檔

### 錯誤 2: `429 Too Many Requests`

**原因：** 超過速率限制（默認 15 RPM）

**響應範例：**
```json
{
  "error": {
    "type": "quota_exceeded",
    "message": "Rate limit exceeded (local guard)",
    "details": {
      "retry_after": 60,
      "source": "local_guard"
    }
  }
}
```

**解決方案：**
1. 等待 60 秒後重試
2. 或修改 `.env` 中的 `RATE_LIMIT_RPM`

### 錯誤 3: `503 Service Unavailable`

**原因：** Gemini API 不可用或 API key 無效

**解決方案：**
1. 檢查 `.env` 中的 `GEMINI_API_KEY`
2. 驗證 API key 是否有效
3. 檢查網絡連接

### 錯誤 4: `400 Validation Error`

**原因：** 請求格式錯誤

**常見問題：**
- 空查詢：`{"query": ""}`
- 查詢太長：超過 1000 字符
- 缺少 Content-Type header

**解決方案：**
```bash
# 正確格式
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Your question here"}'
```

---

## 批量查詢範例

```python
import requests
import time

questions = [
    "What is photosynthesis?",
    "How do async functions work in Python?",
    "What are derivatives?",
    "What caused WWII?"
]

base_url = "http://localhost:8000"

for i, question in enumerate(questions, 1):
    print(f"\n{i}. {question}")
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/query",
            json={"query": question},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"   Answer: {data['data']['answer'][:100]}...")
        print(f"   Latency: {data['metadata']['latency_ms']}ms")
        
        # 避免超過速率限制（15 RPM = 每 4 秒一個請求）
        time.sleep(4)
        
    except Exception as e:
        print(f"   Error: {e}")
```

---

## 進階使用

### 自定義相似度閾值

修改 `.env` 文件：
```env
SIMILARITY_THRESHOLD=0.7  # 默認 0.5，提高以獲得更相關的結果
TOP_K_RESULTS=5           # 默認 3，增加以獲得更多來源
```

### 監控性能

所有響應包含性能指標：
```json
{
  "metadata": {
    "latency_ms": 1234,
    "token_usage": {
      "prompt_tokens": 100,
      "completion_tokens": 50,
      "total_tokens": 150
    }
  }
}
```

### 查看詳細日誌

```bash
# 啟動時設置日誌級別
LOG_LEVEL=DEBUG uvicorn src.courseflow.api.main:app --reload
```

---

## API 文檔

啟動服務後，訪問交互式文檔：

- **Swagger UI**: http://localhost:8000/docs
  - 可直接在瀏覽器中測試 API
  - 查看請求/響應格式
  - 下載 OpenAPI 規範

- **ReDoc**: http://localhost:8000/redoc
  - 美觀的文檔界面
  - 適合閱讀和分享

---

## 下一步

1. 📚 添加自己的文檔到 `docs/` 目錄
2. 🔄 運行 `python scripts/ingest_docs.py` 重新載入
3. 🧪 使用 `python scripts/test_api.py` 驗證
4. 📖 查看 `README.md` 了解更多細節
