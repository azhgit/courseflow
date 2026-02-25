# 貢獻指南

感謝您有興趣為 CourseFlow 做出貢獻！本指南將幫助您參與項目開發。

## 📋 目錄

- [開發工作流程](#-開發工作流程)
- [環境設置](#-環境設置)
- [代碼標準](#-代碼標準)
- [文檔約定](#-文檔約定)
- [提交流程](#-提交流程)

## 🔄 開發工作流程

### 1. 選擇功能分支

CourseFlow 採用分支開發模式，每個功能都有獨立的分支：

```bash
# 查看可用分支
git branch -a

# 切換到功能分支（例如：009-web-scraping）
git checkout 009-web-scraping
```

### 2. 查閱設計文檔

開發前，務必閱讀該分支的設計文檔：

```
specs/{branch-number}-{feature-name}/
├── spec.md              # 功能規格書
├── plan.md              # 實施計劃
├── data-model.md        # 數據模型
├── research.md          # 研究筆記
└── tasks.md             # 任務清單
```

### 3. 進行開發

基於設計文檔進行代碼實現：

```bash
# 創建本地開發分支
git checkout -b feature/my-improvement

# 開發、測試、提交
# ...

# 推送到遠程
git push origin feature/my-improvement
```

### 4. 完成功能

功能完成後，執行以下步驟：

#### A. 編寫或更新功能文檔

```bash
# 如果是新功能分支
touch docs/features/{branch-number}-{feature-name}.md

# 如果是新的測試文檔
touch docs/features/{branch-number}-{feature-name}-testing.md
```

文檔結構參考：

```markdown
# {Branch Number} - {Feature Name}

## 📖 概述
[簡要說明功能]

## 🚀 快速開始
[使用示例]

## 📚 相關資源
[鏈接到設計文檔]
```

#### B. 更新 CHANGELOG

編輯 `docs/CHANGELOG.md`，按 [Keep a Changelog](https://keepachangelog.com/) 格式：

```markdown
## [Unreleased]

### Added
- {分支號} {功能名稱}: 簡要描述

### Fixed
- 修復項目

### Changed
- 變更項目
```

#### C. 提交 PR

```bash
git commit -m "feat({branch}): {description}"
git push origin feature/my-improvement
```

然後在 GitHub 上提交 Pull Request

## 🔧 環境設置

### 前置要求

- Python 3.11+
- Git
- Google Gemini API Key

### 本地開發環境

```bash
# 1. 克隆倉庫
git clone https://github.com/azhgit/courseflow.git
cd courseflow

# 2. 創建虛擬環境
python3.11 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 3. 安裝依賴（含開發工具）
pip install -e ".[dev]"

# 4. 配置環境變量
cp .env.example .env
# 編輯 .env，填入 Gemini API Key
```

### 驗證環境

```bash
# 檢查 Python 版本
python --version

# 導入模塊
python -c "import courseflow; print('✓ OK')"

# 運行測試
pytest tests/ -v --tb=short
```

## 📝 代碼標準

### 代碼風格

- **格式化工具**：Ruff
- **類型檢查**：Mypy
- **Linting**：Ruff

運行檢查：

```bash
# 格式化代碼
ruff format src/ tests/

# Linting
ruff check src/ tests/ --fix

# 類型檢查
mypy src/
```

### 命名約定

```python
# 模塊名：小寫下劃線
my_module.py

# 類名：PascalCase
class MyService:
    pass

# 函數名：snake_case
def my_function():
    pass

# 常量名：UPPER_CASE
MAX_RETRIES = 3
```

### 文檔字符串

```python
def fetch_data(topic: str, limit: int = 10) -> list:
    """
    Fetch data from Wikipedia.
    
    Args:
        topic: The topic to search for
        limit: Maximum number of results
        
    Returns:
        List of matching documents
        
    Raises:
        ValueError: If topic is empty
        TimeoutError: If request times out
    """
    pass
```

### 導入組織

```python
# 1. 標準庫
import os
from typing import Optional

# 2. 第三方庫
import httpx
from pydantic import BaseModel

# 3. 本地模塊
from courseflow.domain.services import MyService
```

## 📚 文檔約定

### 文件結構

```
docs/
├── QUICKSTART.md              # 新手入門
├── CHANGELOG.md               # 版本更新
├── API.md                     # API 文檔
├── ARCHITECTURE.md            # 架構設計
└── features/
    ├── 001-rag-qa.md         # 功能文檔
    └── 001-rag-qa-testing.md # 測試文檔（可選）
```

### 文檔格式

- **標題**：使用 `#` 標記，層級清晰
- **代碼塊**：指定語言類型 ` ```python`
- **鏈接**：相對路徑（例：`../ARCHITECTURE.md`）
- **表格**：使用 Markdown 標準格式

### 中英文混用

- 使用中文編寫面向用戶的文檔（指南、教程）
- 使用英文編寫面向開發者的文檔（API、架構）
- 代碼註解：根據主要語言選擇（Python 代碼用英文）

## ✅ 測試要求

### 測試覆蓋率

- 核心模塊：≥80% 覆蓋率
- 新功能：必須包含單元測試

### 測試運行

```bash
# 運行所有測試
pytest tests/ -v

# 運行特定測試
pytest tests/unit/scraping/ -v

# 生成覆蓋率報告
pytest --cov=src tests/
```

### 測試文件結構

```
tests/
├── unit/                      # 單元測試
│   ├── scraping/
│   │   ├── test_models.py
│   │   └── test_processor.py
│   └── ...
├── integration/               # 集成測試
│   └── scrapers/
└── e2e/                       # 端到端測試
```

## 📤 提交流程

### 1. 分支命名

```
feature/{功能名稱}           # 新功能
bugfix/{bug描述}             # 缺陷修復
docs/{文檔更新}              # 文檔更新
refactor/{重構描述}          # 代碼重構
```

### 2. Commit 消息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
type(scope): subject

body

footer
```

示例：

```
feat(scraper): add Wikipedia scraping support

- Implement MediaWiki API adapter
- Add rate limiting and retry logic
- Support batch document processing

Closes #123
```

**類型說明**：
- `feat`: 新功能
- `fix`: 缺陷修復
- `docs`: 文檔更新
- `refactor`: 代碼重構
- `test`: 測試相關
- `chore`: 構建、依賴等

### 3. Pull Request 檢查清單

在提交 PR 前，請確保：

- [ ] 代碼按照代碼標準格式化
- [ ] 通過了 Linting 和類型檢查
- [ ] 添加或更新了單元測試
- [ ] 測試覆蓋率 ≥80%
- [ ] 更新了相關文檔
- [ ] 更新了 `docs/CHANGELOG.md`
- [ ] Commit 消息清晰且符合規範

### 4. Review 流程

- PR 將由項目維護者審核
- 需要至少 1 個批准才能合併
- 所有 CI 檢查必須通過

## 🐛 報告問題

### Issue 模板

```markdown
## 描述
[簡要描述問題]

## 重現步驟
1. ...
2. ...
3. ...

## 預期行為
[應該發生什麼]

## 實際行為
[實際發生了什麼]

## 環境
- OS: [macOS/Linux/Windows]
- Python: [版本號]
- 分支: [分支名]

## 日誌
[相關日誌輸出]
```

## 📞 聯繫方式

- 📧 Email: [維護者郵箱]
- 💬 Discussions: [GitHub Discussions]
- 🐛 Issues: [GitHub Issues]

## 📖 額外資源

- [Python 代碼風格 PEP 8](https://pep8.org/)
- [FastAPI 文檔](https://fastapi.tiangolo.com/)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
- [Keep a Changelog](https://keepachangelog.com/)

---

感謝您的貢獻！🎉
