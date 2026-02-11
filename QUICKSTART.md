# CourseFlow RAG System - 快速啟動指南

## 前置準備

1. **Python 3.11+** 已安裝
2. **Gemini API Key** - 已在 `.env` 文件中設置

## 步驟 1: 安裝依賴

```bash
# 創建並激活虛擬環境
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 安裝專案依賴
pip install -e ".[dev]"
```

## 步驟 2: 初始化數據庫

```bash
# 確保 data 目錄存在
mkdir -p data

# 初始化 SQLite 數據庫
python scripts/init_db.py
```

## 步驟 3: 載入知識庫文檔

```bash
# 將 docs/ 目錄中的文檔載入 ChromaDB
python scripts/ingest_docs.py
```

**預期輸出**：
```
Loading documents from docs/...
Loaded 10 documents
Generating embeddings using Gemini...
Ingesting documents into ChromaDB...
✅ Successfully ingested 10 documents into ChromaDB
```

## 步驟 4: 啟動 API 服務器

```bash
# 啟動開發服務器（支持熱重載）
uvicorn src.courseflow.api.main:app --reload --host 0.0.0.0 --port 8000
```

**預期輸出**：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting up CourseFlow RAG system...
INFO:     ChromaDB persist dir: ./data/chroma
INFO:     Rate limit: 15 RPM
```

## 步驟 5: 測試 API

### 5.1 檢查健康狀態

```bash
curl http://localhost:8000/api/v1/health
```

**預期響應**：
```json
{
  "status": "ok",
  "services": {
    "chromadb": {
      "status": "ok",
      "document_count": 10
    },
    "sqlite": {
      "status": "ok",
      "queries_last_24h": 0
    },
    "rate_limit": {
      "status": "ok",
      "requests_in_last_minute": 0,
      "max_requests_per_minute": 15,
      "available_requests": 15
    }
  }
}
```

### 5.2 查詢問答（生物學）

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is photosynthesis?"
  }'
```

**預期響應**：
```json
{
  "data": {
    "query_id": "uuid-here",
    "answer": "Photosynthesis is the process by which plants...",
    "sources": [
      {
        "content": "Photosynthesis is the process...",
        "source": "photosynthesis.md",
        "subject": "biology",
        "similarity_score": 0.89
      }
    ]
  },
  "metadata": {
    "latency_ms": 1234,
    "timestamp": "2026-02-11T17:53:00.000Z",
    "token_usage": {
      "prompt_tokens": 150,
      "completion_tokens": 75,
      "total_tokens": 225
    }
  }
}
```

### 5.3 查詢問答（編程）

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do async functions work in Python?"
  }'
```

### 5.4 查詢問答（歷史）

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What caused World War II?"
  }'
```

### 5.5 查看 OpenAPI 文檔

在瀏覽器中打開：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端點總覽

| 端點 | 方法 | 描述 |
|------|------|------|
| `/api/v1/health` | GET | 健康檢查 |
| `/api/v1/query` | POST | RAG 問答 |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc 文檔 |

## 常見問題

### Q: 訪問根路徑 `/` 返回 404
**A**: 根路徑沒有定義端點。請使用：
- `/api/v1/health` - 健康檢查
- `/api/v1/query` - 問答
- `/docs` - API 文檔

### Q: 查詢返回 "No relevant documents found"
**A**: 
1. 確保已運行 `python scripts/ingest_docs.py`
2. 檢查 ChromaDB 是否有文檔：訪問 `/api/v1/health` 查看 `document_count`
3. 嘗試使用與知識庫相關的問題（生物、編程、數學、歷史）

### Q: 查詢返回 429 Rate Limit Error
**A**: 默認限制為 15 RPM。等待 1 分鐘後重試，或修改 `.env` 中的 `RATE_LIMIT_RPM`

### Q: Gemini API 錯誤
**A**: 
1. 檢查 `.env` 中的 `GEMINI_API_KEY` 是否正確
2. 確認 API key 有效且未超過免費配額（15 RPM, 1M TPM）

## 運行測試

```bash
# 運行所有測試
pytest -v

# 運行單元測試
pytest tests/unit/ -v

# 運行集成測試
pytest tests/integration/ -v

# 運行 E2E 測試（需要有效的 GEMINI_API_KEY）
pytest tests/e2e/ -v

# 生成覆蓋率報告
pytest --cov=src/courseflow --cov-report=html
open htmlcov/index.html  # macOS
```

## 停止服務器

在運行 `uvicorn` 的終端中按 `Ctrl+C`

## 清理數據

```bash
# 刪除數據庫和向量存儲（重新開始）
rm -rf data/
```

## 下一步

1. 查看 `/docs` 了解完整 API 規範
2. 添加自己的文檔到 `docs/` 目錄並運行 `python scripts/ingest_docs.py`
3. 查看 `src/courseflow/` 了解代碼結構
4. 閱讀 `README.md` 了解項目詳情
