# 在 Copilot CLI 中使用 Orchestrate Agent

## ✅ 是的，完全可以！

你現在可以在 **Copilot CLI** 中直接使用：

```bash
/speckit.orchestrate "功能描述"
```

---

## 🚀 三種使用方式

### 方式 1️⃣ : 互動模式（推薦）

```bash
$ copilot
copilot> /speckit.orchestrate "實現文檔上傳和去重複檢測系統"
```

**步驟**:
1. 在終端執行 `copilot`
2. 進入互動模式（提示符變為 `copilot>`）
3. 輸入 `/speckit.orchestrate "功能描述"`
4. 系統自動執行完整的 5 階段流程

**優點**:
- ✅ 最直觀的方式
- ✅ 即時看到進度
- ✅ 可隨時中斷（`Ctrl+C`）

---

### 方式 2️⃣ : 非互動模式（快速）

```bash
copilot -p "/speckit.orchestrate \"Document ingestion system\""
```

**特點**:
- 一條指令執行，無需進入互動模式
- 適合自動化腳本或 CI/CD

---

### 方式 3️⃣ : 代理模式

```bash
copilot /agent run speckit.orchestrate -p "Feature description"
```

**特點**:
- 明確指定要執行的 agent
- 適合進階使用

---

## 📋 完整工作流程示例

### 場景：創建「用戶認證系統」

#### 1. 啟動 Copilot
```bash
$ copilot
```

#### 2. 執行 Orchestrate Agent
```bash
copilot> /speckit.orchestrate "實現基於 JWT 的用戶認證系統，包括註冊、登入、刷新 token、權限驗證"
```

#### 3. 系統自動執行
```
🚀 Starting Speckit Pipeline Orchestration

[Stage 1/5] SPECIFY
  → Creating feature specification...
  ✅ Spec created: specs/user-authentication/spec.md

[Stage 2/5] CLARIFY
  Question 1: 是否支持社交登入？
    A) 支持，使用 OAuth 2.0
    B) 不支持，僅用戶名密碼
    C) 未來考慮
  
  Your choice: A
  
  Question 2: Token 過期時間？
    A) 15 分鐘
    B) 1 小時
    C) 自定義
  
  Your choice: B
  
  ... (Q3-Q5 同上，系統等待你的選擇)
  ✅ Clarifications complete

[Stage 3/5] PLAN
  → Designing architecture...
  ✅ Plan created: specs/user-authentication/plan.md

[Stage 4/5] TASKS
  → Generating task list...
  ✅ Tasks created: specs/user-authentication/tasks.md
     Total: 87 tasks

[Stage 5/5] IMPLEMENT
  [████████████████░░░░░░░░░░░░░░░░░░░░░░] 50%
  
  Executing Task 1/87: T001 - Setup project structure
  ✅ T001 completed
  
  Executing Task 2/87: T002 - Create User domain model
  ✅ T002 completed
  
  ... (自動執行所有 87 個任務)
  ✅ Implementation complete: 87/87

✅ PIPELINE COMPLETE!

📊 Summary
├─ Specification: specs/user-authentication/spec.md
├─ Plan: specs/user-authentication/plan.md
├─ Tasks: specs/user-authentication/tasks.md (87 total)
├─ Implementation: All code files generated
└─ Status: ✅ All stages successful

🎉 Next Steps:
   $ git add .
   $ git commit -m "feat: implement user authentication system"
   $ git push origin
```

#### 4. 提交代碼
```bash
copilot> exit

$ git add .
$ git commit -m "feat: implement JWT user authentication system"
$ git push origin
```

---

## 🔍 Agent 檔案驗證

已確認 `speckit.orchestrate.agent.md` 已建立：

```
✅ 位置: .github/agents/speckit.orchestrate.agent.md
✅ 檔案大小: 5,449 bytes
✅ 狀態: 可以立即使用
```

---

## 💡 快速參考

| 場景 | 指令 |
|------|------|
| 在互動模式中 | `/speckit.orchestrate "描述"` |
| 一行指令執行 | `copilot -p "/speckit.orchestrate \"描述\""` |
| 使用特定 agent | `copilot /agent run speckit.orchestrate -p "描述"` |
| 查看 agent 列表 | `copilot /agent list` 或 `/skills list` |
| 重新加載 agents | `copilot /skills reload` |

---

## 🎯 為什麼這樣做有優勢？

### 傳統方式（分離執行）
```bash
# 需要手動執行 5 次指令，每次等待
/speckit.specify "描述"        # 5-10 分鐘
/speckit.clarify               # 2-5 分鐘
/speckit.plan                  # 5-10 分鐘
/speckit.tasks                 # 2-5 分鐘
/speckit.implement             # 20-30 分鐘
# 總耗時: 45-60 分鐘 + 人工監控
```

### 新方式（Orchestrate Agent）
```bash
# 一條指令，完全自動化
/speckit.orchestrate "描述"    # 45-60 分鐘 自動完成
# 你可以邊喝咖啡邊等待
```

**改進**:
- ❌ 不需要手動 5 次指令
- ❌ 不需要在各階段中斷和確認
- ✅ 一次性自動化執行
- ✅ 省時省力

---

## 📌 常見問題

### Q: 我該輸入什麼樣的功能描述？

**好的例子**:
```
/speckit.orchestrate "實現 OAuth 2.0 登入系統，支持 Google、GitHub、Microsoft"

/speckit.orchestrate "建立即時通知系統，包括郵件、推送、應用內通知"

/speckit.orchestrate "實現分佈式文件存儲，支持 S3 和本地備份"
```

**避免**:
```
/speckit.orchestrate "做一個系統"                    # 太模糊
/speckit.orchestrate "hello"                        # 沒有實質信息
```

### Q: Clarify 階段會自動進行嗎？

**是的**，系統會：
1. 顯示澄清問題（通常 Q1-Q5）
2. 提示你選擇 A、B 或 C
3. 等待你的輸入
4. 記錄你的選擇
5. 自動進行到下一階段

### Q: 如果我想修改中間的規格怎麼辦？

可以在任何時候：
1. 中斷流程（`Ctrl+C`）
2. 編輯相關檔案（如 `specs/{feature-slug}/spec.md`）
3. 重新執行 `/speckit.orchestrate`，系統會偵測並恢復

### Q: 整個流程需要多久？

- **Specify**: 5-10 分鐘
- **Clarify**: 2-5 分鐘（需要你回答問題）
- **Plan**: 5-10 分鐘
- **Tasks**: 2-5 分鐘
- **Implement**: 20-30+ 分鐘
- **總計**: 約 45-60 分鐘

### Q: 我可以只執行某個階段嗎？

可以，分別使用：
```bash
/speckit.specify "描述"        # 只執行 Specify
/speckit.clarify               # 只執行 Clarify
/speckit.plan                  # 只執行 Plan
/speckit.tasks                 # 只執行 Tasks
/speckit.implement             # 只執行 Implement
```

---

## 📚 相關檔案

- **Orchestrate Agent 定義**: `.github/agents/speckit.orchestrate.agent.md`
- **完整使用指南**: `SPECKIT_ORCHESTRATION_GUIDE.md`
- **API 上傳指南**: `INGEST_API_GUIDE.md`
- **Bash 輔助腳本**: `scripts/speckit-orchestrate.sh`

---

## ✨ 現在你可以這樣做

```bash
$ copilot
copilot> /speckit.orchestrate "實現新的功能需求"
[系統自動執行所有階段]
✅ 完成！
copilot> exit
$ git push origin
```

**就這麼簡單！** 🚀

---

**準備試試看嗎？**
```bash
$ copilot
copilot> /speckit.orchestrate "Test feature for demonstration"
```

祝你使用愉快！
