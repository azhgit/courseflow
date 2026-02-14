# CourseFlow Ingest API 使用指南

## 快速開始

### 啟動 API 伺服器
```bash
cd /Users/huanganzheng/CourseFlow
uvicorn src.courseflow.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 打開 Swagger UI
```
http://127.0.0.1:8000/docs
```

---

## 📍 Ingest 端點

### 端點資訊
- **URL**: `POST /api/v1/ingest`
- **內容類型**: `multipart/form-data`
- **認證**: 無需認證

### 請求參數

| 參數名 | 類型 | 必須 | 說明 |
|--------|------|------|------|
| `file` | File | ✓ | 要上傳的文檔 |
| `metadata` | String (JSON) | ✓ | 文檔元數據 JSON |

### Metadata 格式
```json
{
  "subject": "programming",
  "difficulty": "intermediate"
}
```

**Metadata 欄位**:
- `subject` (string, required): 主題 slug
  - 支持的主題: `programming`, `biology`, `history`, `general`, 等
  - 小寫字母，允許 `-` 和 `_`
  - 1-50 字符
- `difficulty` (string, optional): 難度標籤 (無驗證限制)

### 支持的文件格式

| 副檔名 | MIME Type | 備註 |
|---------|-----------|------|
| `.md` | `text/markdown` 或 `text/plain` | Markdown 文檔 |
| `.markdown` | `text/markdown` 或 `text/plain` | Markdown 文檔 |
| `.txt` | `text/plain` | 純文本 |
| `.pdf` | `application/pdf` | PDF 文檔 |

### 檔案限制
- **最大大小**: 10 MB
- **自動檢測**: 重複內容自動跳過（SHA-256 內容雜湊）

---

## 📱 Swagger UI 操作步驟

### 步驟 1: 打開 Swagger 文檔
訪問 `http://127.0.0.1:8000/docs`

### 步驟 2: 找到 Ingest 端點
滾動到 **POST /api/v1/ingest** 區域

### 步驟 3: 點擊 "Try it out"

### 步驟 4: 填寫參數

#### 填寫 File 欄位
- 點擊 **Choose File** 按鈕
- 選擇要上傳的 `.md`、`.txt` 或 `.pdf` 文檔

#### 填寫 Metadata 欄位
在文本框中輸入 JSON **（不要加外層引號）**:
```json
{"subject":"programming","difficulty":"intermediate"}
```

或更簡潔：
```json
{"subject":"programming"}
```

### 步驟 5: 執行
- 點擊 **Execute** 按鈕
- 等待響應

---

## 🖥️ 使用 curl 命令

### 上傳 Markdown 文檔
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest" \
  -F "file=@python-guide.md;type=text/plain" \
  -F 'metadata={"subject":"programming","difficulty":"intermediate"}'
```

### 上傳 PDF 文檔
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest" \
  -F "file=@biology-notes.pdf;type=application/pdf" \
  -F 'metadata={"subject":"biology"}'
```

### 上傳純文本文檔
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest" \
  -F "file=@history.txt;type=text/plain" \
  -F 'metadata={"subject":"history"}'
```

### 使用 Python requests
```python
import requests

url = "http://127.0.0.1:8000/api/v1/ingest"

with open("document.md", "rb") as f:
    files = {"file": f}
    data = {"metadata": '{"subject":"programming"}'}
    response = requests.post(url, files=files, data=data)
    print(response.json())
```

---

## ✨ 響應示例

### 成功上傳新文檔 (200 OK)
```json
{
  "success": true,
  "data": {
    "document_id": "f6eeed19-ce69-49e4-98ba-19a583435d8a",
    "filename": "python-guide.md",
    "chunks_created": 8,
    "subject": "programming",
    "ingestion_time_ms": 2340
  },
  "metadata": {
    "request_id": "req_c88e91c7b5f3",
    "timestamp": "2026-02-12T20:27:15.110338+00:00"
  }
}
```

### 重複文檔已跳過 (200 OK)
```json
{
  "success": true,
  "data": {
    "document_id": "f6eeed19-ce69-49e4-98ba-19a583435d8a",
    "filename": "python-guide.md",
    "chunks_created": 0,
    "skipped": true,
    "reason": "Document already indexed"
  },
  "metadata": {
    "request_id": "req_3d413f92379a",
    "timestamp": "2026-02-12T20:27:18.636166+00:00"
  }
}
```

---

## ❌ 錯誤響應

### 400 Bad Request - 驗證失敗
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Unsupported file type. Accepted: .md, .txt, .pdf",
  "details": null
}
```

**常見原因**:
- 檔案格式不支持
- MIME type 不正確
- 檔案大小超過 10 MB
- 主題格式無效

### 400 Bad Request - 缺少必需參數
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Missing metadata field",
  "details": null
}
```

### 429 Too Many Requests - 速率限制
```json
{
  "success": false,
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded (15 requests per minute)",
  "details": null
}
```

### 503 Service Unavailable - 服務錯誤
```json
{
  "success": false,
  "error": "service_unavailable",
  "message": "Failed to process document",
  "details": null
}
```

---

## 🔍 其他相關端點

### 查詢已上傳的文檔
```bash
GET /api/v1/documents
```

### 查詢已定義的主題
```bash
GET /api/v1/subjects
```

### 使用文檔進行 RAG 查詢
```bash
POST /api/v1/query
```

### 串流查詢（SSE）
```bash
POST /api/v1/query/stream
```

範例（curl）：
```bash
curl -N -X POST "http://127.0.0.1:8000/api/v1/query/stream" \
  -H "Content-Type: application/json" \
  -d '{"query":"Explain photosynthesis","conversation_id":null}'
```

SSE 事件型別：
- `chunk`：分段回答
- `sources`：檢索來源
- `done`：完成事件（含 conversation_id、token_count）
- `error`：錯誤事件（例如 `no_relevant_documents`、`rate_limit_exceeded`）

Body:
```json
{
  "text": "什麼是 async/await？",
  "subject": "programming"
}
```

### 健康檢查
```bash
GET /api/v1/health
```

---

## 📌 Swagger UI 常見問題

### ❓ Metadata 應該用什麼格式？

✅ **正確**:
```json
{"subject":"programming","difficulty":"intermediate"}
```

✗ **錯誤** (不要加引號):
```
"{"subject":"programming"}"
```

### ❓ 文件上傳後去哪裡了？

文件被：
1. 提取文本內容
2. 分成多個 chunks（根據句子邊界）
3. 嵌入到 ChromaDB 向量數據庫
4. 元數據保存到 SQLite

查詢時會搜索 ChromaDB 中的相關 chunks。

### ❓ 如果重複上傳同一文件會怎樣？

- 系統計算文件的 SHA-256 內容雜湊
- 如果已存在相同內容，會跳過並返回 `"skipped": true`
- 不會重複插入 chunks

### ❓ 支持哪些主題？

預設主題：
- `programming` (程式設計)
- `biology` (生物學)
- `history` (歷史)
- `general` (通用)

可以使用任何符合格式的新主題。

---

## 🚀 工作流程示例

### 1. 上傳一份 Python 教程
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/ingest" \
  -F "file=@python-tutorial.md" \
  -F 'metadata={"subject":"programming"}'
```

### 2. 確認文檔已上傳
```bash
curl "http://127.0.0.1:8000/api/v1/documents?subject=programming"
```

### 3. 使用 RAG 進行查詢
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{"text":"async/await 是什麼？","subject":"programming"}'
```

### 4. 查看回答
API 會搜索相關 chunks 並使用 LLM 生成答案。

---

## 📊 API 限制

- **速率限制**: 15 requests per minute (全局 quota)
- **最大檔案大小**: 10 MB
- **查詢超時**: 30 秒（包括 LLM 生成時間）
- **最大 chunk 數**: 取決於 Gemini API 月度額度

---

## 🔧 調試技巧

### 檢查 API 健康狀態
```bash
curl http://127.0.0.1:8000/api/v1/health | jq
```

### 查看已上傳文檔
```bash
curl http://127.0.0.1:8000/api/v1/documents | jq
```

### 查看主題列表
```bash
curl http://127.0.0.1:8000/api/v1/subjects | jq
```

### 查看 API 日誌
```bash
# 如果 uvicorn 在終端運行，查看標準輸出中的日誌
```

---

## 📚 更多資源

- OpenAPI 文檔: http://127.0.0.1:8000/docs
- ReDoc 文檔: http://127.0.0.1:8000/redoc
- 代碼倉庫: /Users/huanganzheng/CourseFlow
- API 源碼: `src/courseflow/api/routes/ingest.py`
