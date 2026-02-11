#!/bin/bash
# CourseFlow RAG API 啟動腳本

set -e

PORT=${1:-8000}
HOST=${2:-127.0.0.1}

echo "🚀 啟動 CourseFlow RAG API..."
echo "📍 地址: http://${HOST}:${PORT}"
echo "📖 文檔: http://${HOST}:${PORT}/docs"
echo ""

# 檢查端口是否被占用
if lsof -Pi :${PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  端口 ${PORT} 已被占用！"
    echo ""
    echo "選項："
    echo "  1. 殺掉占用進程: lsof -ti:${PORT} | xargs kill -9"
    echo "  2. 使用其他端口: $0 9000"
    exit 1
fi

# 檢查虛擬環境
if [ -z "${VIRTUAL_ENV}" ]; then
    echo "⚠️  未激活虛擬環境！"
    echo ""
    echo "請先激活虛擬環境："
    echo "  source .venv/bin/activate"
    exit 1
fi

# 檢查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 缺少 .env 文件！"
    echo ""
    echo "請創建 .env 文件並設置 GEMINI_API_KEY"
    exit 1
fi

# 檢查數據目錄
if [ ! -d "data" ]; then
    echo "📁 創建數據目錄..."
    mkdir -p data
fi

# 檢查數據庫
if [ ! -f "data/courseflow.db" ]; then
    echo "🗄️  初始化數據庫..."
    python scripts/init_db.py
fi

# 檢查 ChromaDB
if [ ! -d "data/chroma" ]; then
    echo "📚 載入知識庫文檔..."
    python scripts/ingest_docs.py
fi

echo "✅ 準備就緒！啟動服務器..."
echo ""

# 啟動服務器
uvicorn src.courseflow.api.main:app \
    --host ${HOST} \
    --port ${PORT} \
    --reload
