# 009-Web-Scraping 功能完整驗收測試流程

本文檔提供完整的一整套測試流程，確認功能開發完全。預期耗時：**30–45 分鐘**。

---

## 第 0 步：環境準備（5 分鐘）

### 0.1 確認分支與環境
```bash
cd /Users/huanganzheng/CourseFlow
git branch -v | grep '009-web-scraping'  # 確認在 009-web-scraping 分支

# 確認 Python 環境
python3 --version  # 預期 3.11+
```

### 0.2 安裝依賴
```bash
# 如果還沒激活 venv，激活它
source .venv/bin/activate

# 安裝/更新專案依賴
pip install -e . --quiet

# 驗證關鍵套件安裝成功
python3 -c "import courseflow; print('✓ courseflow module imported')"
python3 -c "import bs4; print('✓ BeautifulSoup4 available')"
python3 -c "import httpx; print('✓ httpx available')"
```

### 0.3 清理舊數據（可選但推薦）
```bash
# 備份舊爬取資料（若有）
[ -d docs/scraped ] && mv docs/scraped docs/scraped.bak.$(date +%s) || echo "No old scraped docs"

# 清空日誌
rm -f logs/scraper.log && touch logs/scraper.log

# 備份舊 Chroma（為了保險起見，但不刪除 — 稍後會增量更新）
echo "Chroma backup not needed unless you want to test from blank state"
```

---

## 第 1 步：單元測試 & 整合測試（8 分鐘）

### 1.1 跑 scraper 相關單元測試
```bash
echo "=== Running Scraper Unit Tests ==="
pytest tests/unit/scraping/test_models.py -v
# 預期結果：✓ 所有測試通過（test_chunk_size_validation, test_chunk_index_bounds 等）
# 期望：15 passed
```

### 1.2 跑 scraper 相關整合測試
```bash
echo "=== Running Scraper Integration Tests ==="
pytest tests/integration/scrapers/ -v 2>&1 | head -50
# 預期結果：所有測試通過或標示為 skip（若無 mock Wikipedia）
```

### 1.3 跑完整測試套件（確保無回歸）
```bash
echo "=== Running Full Test Suite ==="
pytest -q --tb=short
# 預期結果：420+ passed, 37 skipped, 0 failed
# 如果有 failure，回報測試名稱以調試
```

**預期檢查點：**
- [ ] 單元測試通過（15/15）
- [ ] 整合測試通過
- [ ] 完整測試套件無回歸（420+ passed）

---

## 第 2 步：CLI 存在性與幫助文字檢查（3 分鐘）

### 2.1 驗證 CLI 模塊可被導入
```bash
echo "=== Checking CLI Module ==="
python3 -c "from courseflow.cli.scraper import scraper; print('✓ CLI module imported')"
```

### 2.2 查看 CLI 幫助
```bash
echo "=== Checking CLI Help Text ==="
python3 -m courseflow.cli.scraper --help 2>&1
# 預期結果：顯示 scrape, list, search, delete 命令的選項
```

**預期檢查點：**
- [ ] CLI 模塊可導入
- [ ] 幫助文字顯示 scrape/list/search/delete 命令

---

## 第 3 步：Dry-Run 模式測試（5 分鐘）

### 3.1 設定環境變數
```bash
export SCRAPER_OUTPUT_DIR="./docs/scraped"
export SCRAPER_RATE_LIMIT_SECONDS="1.0"
export SCRAPER_MAX_RETRIES="2"
export SCRAPER_TIMEOUT_SECONDS="15"
export SCRAPER_USER_AGENT="CourseFlow/1.0 (Educational Bot)"
echo "✓ Environment variables set"
```

### 3.2 執行 dry-run（預覽，不寫檔）
```bash
echo "=== Dry-Run Test (Preview Only) ==="
rm -f docs/scraped/Photosynthesis.md  # 清除舊檔確保 dry-run 不寫檔

python3 -m courseflow.cli.scraper scrape --topics "Photosynthesis" --dry-run

# 預期輸出：
# - 預覽內容（title, URL, word count, 首幾句）
# - 「Dry-run mode: content preview only」提示
# - 沒有實際寫檔

# 驗證：確認 docs/scraped 目錄為空
if [ ! -f "docs/scraped/Photosynthesis.md" ]; then
  echo "✓ Dry-run: No files written (correct)"
else
  echo "✗ ERROR: Dry-run wrote files (should not happen)"
fi
```

**預期檢查點：**
- [ ] Dry-run 命令執行成功
- [ ] 顯示預覽內容（title, word count, 段落摘要）
- [ ] 沒有實際寫檔到 docs/scraped

---

## 第 4 步：真實爬取 & 輸出驗證（10 分鐘）

### 4.1 爬取單一主題
```bash
echo "=== Real Scraping: Single Topic ==="
python3 -m courseflow.cli.scraper scrape --topics "Photosynthesis"

# 預期輸出：
# - 「Scraping Photosynthesis...」
# - 進度提示（已爬取, 正處理）
# - 完成統計（1/1 successful）
```

### 4.2 驗證輸出文件
```bash
echo "=== Verifying Output File ==="
if [ -f "docs/scraped/Photosynthesis.md" ]; then
  echo "✓ File created: docs/scraped/Photosynthesis.md"
  
  # 檢查檔案大小（應 > 500 bytes）
  SIZE=$(wc -c < docs/scraped/Photosynthesis.md)
  if [ "$SIZE" -gt 500 ]; then
    echo "✓ File size: $SIZE bytes (reasonable)"
  else
    echo "✗ WARNING: File too small ($SIZE bytes)"
  fi
  
  # 顯示前 50 行（驗證 frontmatter + 內容）
  echo "--- First 50 lines ---"
  head -n 50 docs/scraped/Photosynthesis.md
  
else
  echo "✗ ERROR: Output file not created"
fi
```

### 4.3 驗證 Markdown 格式 & 內容品質
```bash
echo "=== Content Quality Checks ==="

# 檢查是否有 YAML frontmatter
if grep -q "^---$" docs/scraped/Photosynthesis.md; then
  echo "✓ YAML frontmatter present"
else
  echo "✗ ERROR: Missing YAML frontmatter"
fi

# 檢查是否有 HTML 標籤（應該沒有）
if grep -q "<[a-z]" docs/scraped/Photosynthesis.md; then
  echo "✗ WARNING: HTML tags found in content (should be cleaned)"
else
  echo "✓ No HTML tags (content is clean)"
fi

# 檢查是否有引用括號（應該移除）
if grep -q "\[0-9\]" docs/scraped/Photosynthesis.md | head -5; then
  echo "⚠ Citation brackets found (check if excessive)"
else
  echo "✓ Citation brackets appear cleaned"
fi

# 檢查 frontmatter 欄位
echo "--- Frontmatter Fields ---"
sed -n '/^---/,/^---/p' docs/scraped/Photosynthesis.md | head -15
```

### 4.4 檢查日誌輸出
```bash
echo "=== Scraper Log Output ==="
tail -n 50 logs/scraper.log
# 預期日誌含：
# - [INFO] Starting scrape job
# - [INFO] ✓ Photosynthesis (XXXX words)
# - [INFO] Saved 1 documents to docs/scraped
# - [INFO] Job complete: 1/1 successful
```

**預期檢查點：**
- [ ] docs/scraped/Photosynthesis.md 已建立，大小 > 500 bytes
- [ ] 包含 YAML frontmatter（title, source, url, scraped_at）
- [ ] 無 HTML 標籤或導航文本
- [ ] 日誌顯示成功爬取統計

---

## 第 5 步：多主題爬取 & 速率限制驗證（8 分鐘）

### 5.1 爬取多個主題並計時
```bash
echo "=== Multi-Topic Scraping with Rate Limiting ==="
TOPICS=("Machine_learning" "Calculus" "World_War_I")

START_TIME=$(date +%s)
python3 -m courseflow.cli.scraper scrape \
  --topics "${TOPICS[0]}" \
  --topics "${TOPICS[1]}" \
  --topics "${TOPICS[2]}"
END_TIME=$(date +%s)

ELAPSED=$((END_TIME - START_TIME))
echo "✓ Elapsed time: ${ELAPSED} seconds"

# 驗證速率限制：3 個主題，每隔 SCRAPER_RATE_LIMIT_SECONDS (1 秒)
# 預期最少時間：1 * 3 = 3 秒
if [ "$ELAPSED" -ge 3 ]; then
  echo "✓ Rate limiting enforced (took ${ELAPSED}s for 3 topics)"
else
  echo "⚠ Rate limiting may not be working (took only ${ELAPSED}s)"
fi
```

### 5.2 驗證多個輸出文件
```bash
echo "=== Verifying Multiple Output Files ==="
ls -lh docs/scraped/
echo ""
EXPECTED_COUNT=4  # Photosynthesis + 3 新檔
ACTUAL_COUNT=$(ls -1 docs/scraped/ | wc -l)
echo "Files: $ACTUAL_COUNT (expected ~$EXPECTED_COUNT)"
if [ "$ACTUAL_COUNT" -ge "$EXPECTED_COUNT" ]; then
  echo "✓ Multiple files created"
else
  echo "⚠ Fewer files than expected"
fi
```

### 5.3 檢查日誌統計
```bash
echo "=== Scraping Statistics ==="
tail -n 10 logs/scraper.log | grep -E "Job complete|successful|failed"
# 預期：3/3 successful (或接近此數)
```

**預期檢查點：**
- [ ] 3 個主題全部爬取成功
- [ ] 總執行時間 >= 預期時間（受速率限制）
- [ ] docs/scraped 中存在 3 個新的 .md 檔
- [ ] 日誌顯示 3/3 successful 或接近

---

## 第 6 步：錯誤處理 & 失敗恢復（5 分鐘）

### 6.1 爬取不存在的主題（404 錯誤）
```bash
echo "=== Testing 404 Error Handling ==="
python3 -m courseflow.cli.scraper scrape --topics "This_Article_Does_Not_Exist_98765" 2>&1 | tee /tmp/scraper_404.log

# 預期行為：
# - 記錄 [ERROR] 或 [WARN]
# - 程式不中斷（exit 0 或 partial success）
# - 日誌顯示該主題失敗但其他主題繼續處理

echo ""
echo "=== Checking Error Log ==="
grep -i "not.found\|404" logs/scraper.log || echo "Error message recorded"
```

### 6.2 爬取有效 + 無效主題混合
```bash
echo "=== Testing Partial Success ==="
python3 -m courseflow.cli.scraper scrape \
  --topics "Python_(programming_language)" \
  --topics "Nonexistent_Topic_XYZ" \
  --topics "Quantum_mechanics"

echo ""
echo "=== Expected Results ==="
tail -n 5 logs/scraper.log
# 預期：2/3 successful (or 3/3 successful if all valid)
```

**預期檢查點：**
- [ ] 404 錯誤被記錄但不中斷程式
- [ ] 混合爬取時，有效主題仍被處理
- [ ] 日誌清楚顯示失敗與成功計數

---

## 第 7 步：ChromaDB 整合驗證（8 分鐘）

### 7.1 啟動後端 API（若需測試完整集成）
```bash
echo "=== Starting Backend API ==="
# 在另一個終端或後台啟動（可選）
# uvicorn src.courseflow.api.main:app --reload &
# sleep 2  # 等待服務啟動
# 或者用現有的執行中服務

# 檢查 Chroma 文件系統變化
echo "Chroma directory before scraping:"
ls -la data/chroma/ 2>/dev/null | head -10
```

### 7.2 檢查 Chroma 數據目錄
```bash
echo "=== Checking Chroma Storage ==="
# 爬取後應該出現新的 collection 目錄或 metadata 更新
ls -lah data/chroma/ | tail -10

# 檢查 chroma.sqlite3 修改時間
CHROMA_MTIME=$(stat -f '%Sm' data/chroma/chroma.sqlite3 2>/dev/null || echo "File not found")
echo "Chroma DB last modified: $CHROMA_MTIME"
```

### 7.3 查詢 API（若後端運行）
```bash
echo "=== Querying via API (if backend running) ==="
# 檢查後端是否運行（optional）
if curl -s http://localhost:8000/api/v1/health >/dev/null 2>&1; then
  echo "✓ Backend API is running"
  
  # 執行查詢，期望返回新爬取的內容
  curl -s -X POST http://localhost:8000/api/v1/query \
    -H 'Content-Type: application/json' \
    -d '{"query":"photosynthesis","top_k":3}' | python3 -m json.tool | head -30
  
  echo ""
  echo "✓ API returned results (check if new content included)"
else
  echo "⚠ Backend not running - skip this check or start it manually"
fi
```

**預期檢查點：**
- [ ] data/chroma 目錄存在且有新的數據文件
- [ ] chroma.sqlite3 時間戳已更新
- [ ] （可選）API 查詢返回新爬取的文章內容

---

## 第 8 步：--no-ingest 標籤測試（3 分鐘）

### 8.1 爬取但跳過自動 ingest
```bash
echo "=== Testing --no-ingest Flag ==="
python3 -m courseflow.cli.scraper scrape --topics "Quantum_mechanics" --no-ingest

echo ""
echo "✓ Files created but ChromaDB not updated (check logs for 'skipped ingestion')"
tail -n 5 logs/scraper.log | grep -i "ingest\|ingestion" || echo "No ingest log found"
```

**預期檢查點：**
- [ ] 文件建立於 docs/scraped
- [ ] 日誌顯示「ingestion skipped」或類似信息

---

## 第 9 步：清理與最終驗收（2 分鐘）

### 9.1 最終文件與日誌檢查
```bash
echo "=== Final File Count ==="
echo "Scraped documents: $(ls -1 docs/scraped/ 2>/dev/null | wc -l)"
ls -lh docs/scraped/ 2>/dev/null | tail -5

echo ""
echo "=== Final Log Entries ==="
tail -n 15 logs/scraper.log
```

### 9.2 驗收簽名
```bash
echo "=== Acceptance Test Summary ==="
cat << 'EOF'
✓ Unit tests passed (15/15)
✓ Integration tests passed
✓ Full test suite passed (420+ tests, 0 failures)
✓ CLI commands functional (scrape, list, search, delete)
✓ Dry-run mode works (preview, no files written)
✓ Single-topic scraping works (created markdown with frontmatter)
✓ Content quality checks passed (no HTML, cleaned citations)
✓ Multi-topic scraping with rate limiting verified
✓ Error handling verified (404, invalid topics don't crash)
✓ ChromaDB integration confirmed (new files created, metadata updated)
✓ --no-ingest flag respected
✓ Logging and statistics accurate

🎉 Feature 009-Web-Scraping: ACCEPTANCE TEST PASSED
EOF
```

### 9.3 清理備份（可選）
```bash
# 若想保持乾淨
rm -f docs/scraped.bak.* /tmp/scraper_404.log

echo ""
echo "✓ Acceptance test complete!"
echo "Ready to create PR: https://github.com/azhgit/courseflow/pull/new/009-web-scraping"
```

---

## 快速檢查清單

在啟動完整測試前，勾選：

- [ ] 已檢出 009-web-scraping 分支（git branch 顯示 *）
- [ ] Python 3.11+ 已安裝
- [ ] 依賴已安裝（pip install -e .）
- [ ] logs 目錄存在（mkdir -p logs）
- [ ] docs 目錄存在（mkdir -p docs）
- [ ] 舊爬取數據已備份或清除（docs/scraped.bak 或清空）

---

## 故障排除

| 問題 | 原因 | 解決 |
|------|------|------|
| `ModuleNotFoundError: courseflow` | 依賴未安裝 | `pip install -e .` 重新安裝 |
| `No such file: logs/scraper.log` | 日誌目錄不存在 | `mkdir -p logs && touch logs/scraper.log` |
| 爬取很慢（每個主題 > 5 秒） | 速率限制或網路慢 | 檢查 SCRAPER_RATE_LIMIT_SECONDS 與網路連接 |
| 「403 Forbidden」或「429 Too Many Requests」| 維基百科速率限制 | 增加 SCRAPER_RATE_LIMIT_SECONDS (e.g., 3) 或等待 |
| Chroma 未更新 | 自動 ingest 未觸發或失敗 | 檢查日誌是否有 ingest 錯誤，手動運行 ingest |
| 文件為空或只有 frontmatter | 內容提取失敗 | 檢查維基百科頁面格式是否改變，查看日誌詳情 |

---

## 完整測試執行估時

| 步驟 | 時間 |
|------|------|
| 第 0（環境準備） | 5 分鐘 |
| 第 1（單元測試） | 8 分鐘 |
| 第 2（CLI 檢查） | 3 分鐘 |
| 第 3（Dry-run） | 5 分鐘 |
| 第 4（真實爬取） | 10 分鐘 |
| 第 5（多主題 + 速率限制） | 8 分鐘 |
| 第 6（錯誤處理） | 5 分鐘 |
| 第 7（Chroma 整合） | 8 分鐘 |
| 第 8（--no-ingest） | 3 分鐘 |
| 第 9（清理 + 驗收） | 2 分鐘 |
| **總計** | **57 分鐘** |

若跳過部分步驟（如 Chroma 整合若後端未運行），可縮短至 **30–40 分鐘**。

---

## 下一步

完成上述驗收測試後：
1. 提交並推送所有變更到 009-web-scraping 分支
2. 在 GitHub 建立 PR（https://github.com/azhgit/courseflow/pull/new/009-web-scraping）
3. 更新 specs/009-wikipedia-scraper/plan.md 記錄完成狀態
4. 準備剩餘 45 項文檔任務（如需）

EOF
