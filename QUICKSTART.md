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
| `/api/v1/quota/status` | GET | 配額狀態 |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc 文檔 |

## 配額保護（Demo 模式）

CourseFlow 包含演示配額保護機制，防止在直播演示中用盡 API 配額。

### 基本限制

| 項目 | 限制 | 說明 |
|------|------|------|
| 每IP限制 | 20 請求/小時 | 使用滑動窗口追蹤 |
| 每日預算 | 300 請求/天 | 全局限制，在午夜 UTC 重置 |
| 快取問題 | 10 個預加載問題 | 繞過速率限制與配額 |

### 快取命中

預加載的問題會自動檢測並返回快取答案，**不計入配額**：

```bash
# 這會返回快取答案（如果匹配）
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is async/await in Python?"}'

# 觀察響應頭：
# X-Cache-Hit: true （表示使用了快取）
# X-RateLimit-Remaining: 20 （配額未減少）
```

### 檢查配額狀態

```bash
# 獲取當前配額使用情況
curl http://localhost:8000/api/v1/quota/status
```

**預期響應**：
```json
{
  "daily": {
    "used": 5,
    "limit": 300,
    "remaining": 295,
    "percentage_used": 1.67,
    "reset_at": "2026-02-17T00:00:00+00:00"
  },
  "cache": {
    "questions_count": 10,
    "hit_rate": 20.0
  },
  "quota_warning": false,
  "timestamp": "2026-02-16T19:53:00.000000+00:00"
}
```

### 達到 IP 限制

```bash
# 在同一 IP 快速發送 20+ 請求
for i in {1..25}; do
  curl -X POST http://localhost:8000/api/v1/query \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Question $i\"}"
done

# 第 21 個請求返回：
# HTTP/1.1 429 Too Many Requests
# Retry-After: 3456 （秒數）
# {
#   "error": "Per-IP hourly limit exceeded",
#   "current": 20,
#   "limit": 20,
#   "retry_after_seconds": 3456
# }
```

### 配額警告（80%+ 使用）

當日使用率達到 80% 時，健康檢查返回警告：

```bash
curl http://localhost:8000/health

# 當配額 >= 80% 使用時：
{
  "success": true,
  "data": {
    "status": "healthy",
    "quota_warning": true,
    "components": { ... }
  }
}
```

### 配置配額設置

編輯 `.env` 文件：

```env
# 演示模式（默認）
QUOTA_HOURLY_LIMIT=100
QUOTA_DAILY_BUDGET=300
QUOTA_CACHE_ENABLED=true
QUOTA_STREAM_DELAY_MS=30
LOCAL_UNLIMITED=true      # 本地測試關閉用量限制

# 開發測試
QUOTA_HOURLY_LIMIT=5         # 容易達到限制
QUOTA_DAILY_BUDGET=20        # 容易耗盡
QUOTA_CACHE_ENABLED=true
QUOTA_STREAM_DELAY_MS=5      # 快速測試

# 壓力測試
QUOTA_HOURLY_LIMIT=100
QUOTA_DAILY_BUDGET=1000
QUOTA_CACHE_ENABLED=false    # 禁用快取
QUOTA_STREAM_DELAY_MS=0      # 即時交付
```

### 測試配額流程

```bash
# 1. 檢查初始配額
curl http://localhost:8000/api/v1/quota/status | jq '.daily.used'
# 輸出: 0

# 2. 發送一個查詢
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?"}'

# 3. 檢查更新後的配額
curl http://localhost:8000/api/v1/quota/status | jq '.daily.used'
# 輸出: 1 (或 0 如果命中快取)

# 4. 檢查快取命中率
curl http://localhost:8000/api/v1/quota/status | jq '.cache.hit_rate'
# 輸出: 50.0 (取決於快取匹配)
```

---

## API 端點總覽

| 端點 | 方法 | 描述 |
|------|------|------|
| `/api/v1/health` | GET | 健康檢查 |
| `/api/v1/query` | POST | RAG 問答 |
| `/api/v1/quota/status` | GET | 配額狀態 |
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
