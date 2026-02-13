# Speckit 完整流程串聯指南

你現在有 **3 種方式** 執行完整的 speckit 流程（specify → clarify → plan → tasks → implement）：

## 方式 1️⃣ : 使用 Orchestrate Agent（推薦）🚀

**最簡單、全自動的方式**

```bash
/speckit.orchestrate "你的功能描述"
```

### 例子
```bash
/speckit.orchestrate "實現文檔上傳和去重複檢測功能"
```

### 特點
✅ 完全自動化 5 個流程階段  
✅ 自動處理階段轉換  
✅ 智能提示用戶互動（如 clarify 的 Q&A）  
✅ 即時進度更新  
✅ 總耗時：45-60 分鐘

### 流程
```
🚀 啟動 Orchestrate Agent
  ↓
[Stage 1] Specify (5-10 分鐘)
  → 創建功能規格 (spec.md)
  ↓
[Stage 2] Clarify (2-5 分鐘，含互動)
  → 解決不明確之處 (Q1-Q5)
  ↓
[Stage 3] Plan (5-10 分鐘)
  → 設計系統架構 (plan.md)
  ↓
[Stage 4] Tasks (2-5 分鐘)
  → 生成任務列表 (tasks.md, 通常 80+ 個任務)
  ↓
[Stage 5] Implement (20-30+ 分鐘)
  → 自動執行所有任務
  ↓
✅ 完成！所有檔案已生成
```

---

## 方式 2️⃣ : 手動逐階段執行

**保有完全控制、可隨時暫停的方式**

### Step 1: 執行 Specify
```bash
/speckit.specify "你的功能描述"
```
**輸出**: `specs/{feature-slug}/spec.md`

等待 specify 完成後，才進行 Step 2。

### Step 2: 執行 Clarify
```bash
/speckit.clarify
```
**互動**: 回答 5 個問題 (A/B/C 選擇)  
**輸出**: `specs/{feature-slug}/checklist.md`

### Step 3: 執行 Plan
```bash
/speckit.plan
```
**輸出**: `specs/{feature-slug}/plan.md`

### Step 4: 執行 Tasks
```bash
/speckit.tasks
```
**輸出**: `specs/{feature-slug}/tasks.md`  
**內容**: 結構化的任務列表 (通常 80+ 個)

### Step 5: 執行 Implement
```bash
/speckit.implement
```
**輸出**: 所有源代碼、測試、文檔檔案  
**耗時**: 20-30+ 分鐘

---

## 方式 3️⃣ : 使用 Bash 腳本工具

**適用於 macOS/Linux 環境的腳本工具集**

```bash
# 初始化實現計劃
./.specify/scripts/bash/setup-plan.sh

# 驗證前置條件
./.specify/scripts/bash/check-prerequisites.sh

# 更新 AI 代理上下文
./.specify/scripts/bash/update-agent-context.sh
```

**功能**:
- 支援 macOS、Linux、WSL2 環境
- 提供完整的功能架構設置
- 驗證依賴檔案和分支命名
- 自動更新 AI 代理的上下文信息

詳見: [Bash 腳本文檔](./.specify/scripts/bash/README.md)

---

## 🎯 對比表

| 特性 | Orchestrate Agent | 手動逐步 | Bash 腳本工具 |
|------|------------------|---------|-------------|
| 完全自動化 | ✅ 是 | ❌ 否 | ❌ 否 |
| 總耗時 | 45-60 分鐘 | 同上（分散執行） | - |
| 需要互動 | 少（仅 clarify） | 多（每階段確認） | ❌ 否 |
| 錯誤恢復 | 自動重試 | 可中斷後恢復 | 手動恢復 |
| 適用場景 | 首次創建功能 | 需要細緻控制 | macOS/Linux 環境設置 |

---

## 📋 完整工作流程範例

假設你要創建「用戶認證系統」功能：

### 使用 Orchestrate Agent
```bash
/speckit.orchestrate "實現基於 JWT 的用戶認證系統，包括註冊、登入、刷新 token"
```

**系統會自動**:
1. 建立 `specs/user-authentication/spec.md`
2. 問你 5 個澄清問題 (選 A/B/C)
3. 生成設計架構
4. 列出所有實作任務
5. 自動執行所有任務（建立代碼、測試等）
6. 提示你進行 git commit

**預期產出**:
```
src/courseflow/
├── application/auth_service.py
├── api/routes/auth.py
├── infrastructure/repositories/user_repo.py
└── ...

tests/
├── unit/test_auth_service.py
├── integration/test_auth_endpoints.py
└── ...

specs/user-authentication/
├── spec.md
├── plan.md
├── tasks.md (含所有任務狀態)
└── checklist.md
```

---

## 🔄 什麼時候用哪種方式

### 用 Orchestrate Agent 當：
- ✅ 這是新功能（從零開始）
- ✅ 你希望完全自動化
- ✅ 你有 1 小時的完整時間
- ✅ 你只需回答幾個澄清問題

### 用手動逐步當：
- ✅ 你需要在 clarify 時詳細檢視
- ✅ 你想在某個階段暫停
- ✅ 你需要對設計有細緻控制
- ✅ 你在學習 speckit 流程

### 用 Bash 腳本工具當：
- ✅ 你使用 macOS 或 Linux 系統
- ✅ 你需要設置功能架構
- ✅ 你想驗證前置條件
- ✅ 你要更新 AI 代理上下文

---

## 🚀 我的推薦

對於 CourseFlow 項目：

### 新功能推薦流程
```bash
# 1. 啟動完全自動化流程
/speckit.orchestrate "功能描述"

# 2. 監控輸出並回答 clarify 問題（約 5 分鐘）
# 此時系統會問你 5 個 A/B/C 問題

# 3. 等待 implement 完成（約 20-30 分鐘）
# 你可以邊喝咖啡邊看進度

# 4. 完成後自動提示
git add . && git commit -m "feat: 完整功能名稱"
git push origin
```

### 時間估算
```
總時間 = 45-60 分鐘
├─ Specify: 5-10 分鐘
├─ Clarify: 2-5 分鐘 (互動)
├─ Plan: 5-10 分鐘
├─ Tasks: 2-5 分鐘
└─ Implement: 20-30+ 分鐘
```

---

## 📌 常見問題

### Q: 我可以在 clarify 或 implement 階段中斷嗎？
**A**: 可以。用 `Ctrl+C` 中斷，下次執行時會提示恢復從上一個完成的階段。

### Q: 如果某個階段失敗怎麼辦？
**A**: Orchestrate Agent 會自動重試失敗的階段。如果連續失敗，會提示你檢視錯誤日誌。

### Q: 是否可以修改中間生成的檔案（如 spec.md）？
**A**: 可以。修改後只需重新啟動該階段。例如改了 spec.md，重新執行 `/speckit.clarify`。

### Q: Tasks 為什麼有 80+ 個任務？
**A**: 這是正常的。Speckit 會細分為：
- 基礎設置（10-15 個任務）
- 功能實作（30-50 個任務）
- 測試（15-25 個任務）
- 文檔和優化（5-10 個任務）

### Q: 我只想執行某些階段可以嗎？
**A**: 可以。分別執行：
```bash
/speckit.specify "描述"    # 只做 Specify
/speckit.clarify           # 只做 Clarify
/speckit.plan              # 只做 Plan
/speckit.tasks             # 只做 Tasks
/speckit.implement         # 只做 Implement
```

---

## 📚 相關文檔

- **API 上傳指南**: `INGEST_API_GUIDE.md`
- **項目規格**: `specs/{feature-slug}/spec.md`
- **代碼貢獻**: `README.md`
- **項目憲章**: `.specify/memory/constitution.md`

---

## ✨ 新增功能特性

### Orchestrate Agent 特性
- 🔄 自動階段轉換
- 📊 實時進度顯示
- 🎯 智能錯誤恢復
- 💾 自動保存中間產物
- 📝 詳細執行日誌

### 與傳統流程的改進
```
傳統方式:
  /specify → 等候 → /clarify → 等候 → /plan → 等候 → /tasks → 等候 → /implement
  ❌ 繁瑣，容易中斷

新方式:
  /orchestrate "描述" → [自動流程所有階段] → ✅ 完成
  ✅ 簡潔，完全自動化
```

---

**準備好開始了嗎？** 
```bash
/speckit.orchestrate "你的功能描述"
```

祝你開發順利！🚀
