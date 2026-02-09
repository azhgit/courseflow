# CourseFlow RAG 測試指南

## 已修復的問題清單 ✅

### 1. 模型結構調整
- ✅ `DocumentMetadata.total_chunks` 改為可選（Optional）
- ✅ `Document.id` 統一（原為 doc_id）
- ✅ `Document.embedding` 支援 768-3072 維度
- ✅ `Document.content` 上限提高到 10000 字元
- ✅ 所有測試檔案 import 路徑修正：`src.courseflow` → `courseflow`
- ✅ RateLimitTracker 屬性名稱修正

### 2. Gemini API 配置
- ✅ Embedding 模型更新為 `models/gemini-embedding-001`
- ✅ API endpoint 路徑修正
- ✅ 文件載入成功（10 份文件，17 個 chunks）

## 測試步驟

### 前置準備（已完成）
```bash
# 1. 環境變數已設定
cat .env  # 確認 GEMINI_API_KEY 存在

# 2. 依賴已安裝
pip install -e ".[dev]"

# 3. 資料庫已初始化
python scripts/init_db.py

# 4. 文件已載入
python scripts/ingest_docs.py  # 17 chunks loaded
```

### 執行測試

#### 1. 單元測試（Unit Tests）
```bash
# 測試所有單元測試
pytest tests/unit/ -v

# 僅測試模型
pytest tests/unit/test_models.py -v  # ✅ 15/15 passed

# 僅測試 RAG 服務
pytest tests/unit/test_rag_service.py -v
```

#### 2. 整合測試（Integration Tests）
```bash
# 測試所有整合測試
pytest tests/integration/ -v

# 測試 ChromaDB 向量搜尋
pytest tests/integration/test_chroma.py -v

# 測試 SQLite 查詢儲存庫
pytest tests/integration/test_sqlite.py -v

# 測試 API 端點
pytest tests/integration/test_api_query.py -v
```

#### 3. E2E 測試（End-to-End Tests）
```bash
# 完整 RAG 流程測試
pytest tests/e2e/test_rag_pipeline.py -v
```

#### 4. 全部測試 + 覆蓋率報告
```bash
# 運行所有測試並產生覆蓋率報告
pytest -v --cov=src/courseflow --cov-report=html --cov-report=term-missing

# 查看 HTML 覆蓋率報告
open htmlcov/index.html
```

### 手動 API 測試

#### 啟動伺服器
```bash
# 終端機 1：啟動 FastAPI
uvicorn src.courseflow.api.main:app --reload

# 或使用 courseflow（如果已安裝為套件）
uvicorn courseflow.api.main:app --reload
```

#### 測試端點

```bash
# 1. 健康檢查
curl http://localhost:8000/api/v1/health

# 2. 查詢生物學問題
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is photosynthesis?"}'

# 3. 查詢程式設計問題
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How to use async/await in Python?"}'

# 4. 查詢歷史問題
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What happened in World War II?"}'

# 5. 查詢數學問題
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are derivatives in calculus?"}'
```

#### 使用 Swagger UI
```bash
# 打開瀏覽器訪問
open http://localhost:8000/docs

# 可以直接在 UI 中測試 API
```

### 預期結果

#### 成功回應範例
```json
{
  "success": true,
  "data": {
    "answer": "Photosynthesis is the process...",
    "sources": [
      {
        "document": {
          "id": "biology-photosynthesis-chunk-0",
          "content": "...",
          "metadata": {
            "source": "docs/biology/photosynthesis.md",
            "subject": "biology",
            "chunk_index": 0
          }
        },
        "similarity_score": 0.87
      }
    ],
    "retrieval_count": 3
  },
  "metadata": {
    "request_id": "req_1234567890",
    "timestamp": "2026-02-09T17:00:00Z",
    "latency_ms": 1234,
    "token_count": 567
  },
  "error": null
}
```

#### 錯誤回應範例（404 - 找不到相關文件）
```json
{
  "success": false,
  "data": null,
  "metadata": {
    "request_id": "req_1234567890",
    "timestamp": "2026-02-09T17:00:00Z"
  },
  "error": {
    "code": "no_relevant_documents",
    "message": "No relevant information found in knowledge base"
  }
}
```

#### 錯誤回應範例（429 - 超過限流）
```json
{
  "success": false,
  "data": null,
  "metadata": {
    "request_id": "req_1234567890",
    "timestamp": "2026-02-09T17:00:00Z"
  },
  "error": {
    "code": "quota_exceeded",
    "message": "Gemini API quota exceeded (15 RPM). Retry later.",
    "retry_after": 60
  }
}
```

## 參考文件

### 主要文件
- **快速開始**：`specs/001-rag-qa/quickstart.md`
- **任務清單**：`specs/001-rag-qa/tasks.md`
- **API 契約**：`specs/001-rag-qa/contracts/openapi.yaml`
- **資料模型**：`specs/001-rag-qa/data-model.md`
- **研究決策**：`specs/001-rag-qa/research.md`

### 測試相關
- **Golden Dataset**：`tests/fixtures/golden_qa_pairs.json`（14 組問答）
- **單元測試**：`tests/unit/`
- **整合測試**：`tests/integration/`
- **E2E 測試**：`tests/e2e/`

## 目前狀態

### ✅ 已完成（Phase 1-2 + 部分 Phase 3）
- Phase 1: Setup（專案結構、依賴、範例文件）
- Phase 2: Foundational（領域模型、埠、適配器、API 基礎）
- Phase 3 測試：模型單元測試 ✅ 15/15 passed

### 🚧 待完成
- Phase 3: 其他測試（RAG service、integration、E2E）
- Phase 3: 實作（LLM client、RAG service、Query endpoint）已實作，待測試驗證
- Phase 4: Rate Limiting
- Phase 5: Error Handling
- Phase 6: Polish

### 🎯 下一步
1. 運行整合測試驗證 ChromaDB 和 API
2. 運行 E2E 測試驗證完整流程
3. 修復任何失敗的測試
4. 繼續 Phase 4-6 實作

## 常見問題

### Q: 測試失敗：No module named 'src'
A: 已修復，所有 import 已改為 `from courseflow.domain...`

### Q: Document validation error: content too short
A: 已修復，所有測試內容已更新為 100+ 字元

### Q: DocumentMetadata missing total_chunks
A: 已修復，total_chunks 現在是可選欄位

### Q: Gemini API 404 error
A: 已修復，embedding 模型已更新為 `models/gemini-embedding-001`

### Q: 如何重新載入文件？
```bash
rm -rf data/chroma/*  # 清除舊資料
python scripts/ingest_docs.py  # 重新載入
```
