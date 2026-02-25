# 001 - RAG Q&A 系統

> 檢索增強生成（RAG）核心系統

## 📖 概述

**001-rag-qa** 是 CourseFlow 的核心功能，實現了一個完整的 RAG（Retrieval-Augmented Generation）系統，使系統能夠從知識庫中檢索相關文檔，並使用 AI 模型生成有根據的答案。

### 功能亮點

- 🎯 **向量相似度檢索**：使用 ChromaDB 進行高效語義搜索
- 🤖 **AI 生成答案**：使用 Google Gemini 生成高質量回答
- 📖 **來源引用**：自動提供答案的參考文獻
- ⚡ **低延遲**：<2s P95 查詢延遲
- 🔐 **源隔離**：防止模型虛構（Hallucination）

## 🚀 快速開始

### 基本查詢

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is photosynthesis?"}'
```

### 響應示例

```json
{
  "query": "What is photosynthesis?",
  "answer": "Photosynthesis is the process...",
  "sources": [
    {
      "document": "Photosynthesis.md",
      "relevance": 0.92
    }
  ],
  "latency_ms": 1250
}
```

## 📚 相關資源

- [完整 API 文檔](../API.md)
- [架構設計](../ARCHITECTURE.md)
- [設計文檔](../../specs/001-rag-qa/)

---

**維護者**：CourseFlow 開發團隊
