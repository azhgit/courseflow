# 🚀 CourseFlow 快速啟動

## 一分鐘啟動指南

```bash
# 1. 激活虛擬環境
source .venv/bin/activate

# 2. 啟動服務器（使用啟動腳本）
./scripts/start.sh

# 或手動啟動
uvicorn src.courseflow.api.main:app --host 127.0.0.1 --port 8000 --reload
```

**服務器啟動後：**
- 🏥 健康檢查: http://localhost:8000/api/v1/health
- 📖 API 文檔: http://localhost:8000/docs
- 💬 問答端點: http://localhost:8000/api/v1/query

## 快速測試

```bash
# 運行自動化測試
python scripts/test_api.py

# 或手動測試
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is photosynthesis?"}'
```

## 重要提示

❌ **不要訪問根路徑 `/`** - 會返回 404

✅ **使用正確的端點：**
- `/api/v1/health` - 健康檢查
- `/api/v1/query` - 問答
- `/docs` - Swagger UI
- `/redoc` - ReDoc 文檔

## 可用主題

系統已載入以下領域的知識：
- 🧬 **生物學**: 光合作用、細胞分裂
- 💻 **編程**: Python 函數、異步編程、OOP
- 📐 **數學**: 導數、矩陣
- 📜 **歷史**: 二戰、冷戰、法國大革命

## 範例查詢

```bash
# 生物學
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is photosynthesis?"}'

# 編程
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do async functions work in Python?"}'

# 數學
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are derivatives?"}'

# 歷史
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What caused World War II?"}'
```

## 故障排除

### 端口被占用
```bash
# 殺掉占用進程
lsof -ti:8000 | xargs kill -9

# 或使用其他端口
./scripts/start.sh 9000
```

### 429 速率限制
默認限制為 **15 請求/分鐘**。等待 60 秒或修改 `.env` 中的 `RATE_LIMIT_RPM`。

### 找不到相關文檔
確保查詢與知識庫主題相關（生物、編程、數學、歷史）。

## 詳細文檔

- 📘 **完整指南**: [QUICKSTART.md](QUICKSTART.md)
- 💡 **使用範例**: [EXAMPLES.md](EXAMPLES.md)
- 📚 **項目 README**: [README.md](README.md)
- 🧪 **測試文檔**: [TESTING.md](TESTING.md)

## 測試腳本

```bash
# 測試所有功能（推薦）
python scripts/test_api.py

# 測試指定端口
python scripts/test_api.py 9000
```

測試腳本會自動驗證：
- ✅ 健康檢查
- ✅ 生物學、編程、數學、歷史查詢
- ✅ 無關問題處理
- ✅ 性能指標

## 下一步

1. ✨ 查看 `/docs` 探索完整 API
2. 📝 閱讀 `EXAMPLES.md` 學習高級用法
3. 🔧 修改 `.env` 自定義配置
4. 📚 添加自己的文檔到 `docs/` 並運行 `python scripts/ingest_docs.py`
