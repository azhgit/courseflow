#!/usr/bin/env python3
"""
CourseFlow RAG API 測試腳本

使用方法:
    python scripts/test_api.py [端口號]

範例:
    python scripts/test_api.py          # 默認使用 8000 端口
    python scripts/test_api.py 9000     # 使用 9000 端口
"""

import sys
import json
import requests
from typing import Any


def test_health(base_url: str) -> bool:
    """測試健康檢查端點"""
    print("\n" + "=" * 60)
    print("1️⃣  測試健康檢查: GET /api/v1/health")
    print("=" * 60)
    
    try:
        response = requests.get(f"{base_url}/api/v1/health", timeout=5)
        response.raise_for_status()
        
        data = response.json()
        print(f"✅ 狀態: {data['status']}")
        print(f"📊 ChromaDB 文檔數: {data['services']['chromadb']['document_count']}")
        print(f"📈 過去24小時查詢數: {data['services']['sqlite']['queries_last_24h']}")
        print(f"🔄 可用請求數: {data['services']['rate_limit']['available_requests']}/{data['services']['rate_limit']['max_requests_per_minute']}")
        
        return True
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False


def test_query(base_url: str, question: str, test_name: str) -> bool:
    """測試問答端點"""
    print("\n" + "=" * 60)
    print(f"2️⃣  測試問答: {test_name}")
    print("=" * 60)
    print(f"❓ 問題: {question}")
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/query",
            json={"query": question},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\n✅ 回答:")
        print(f"{data['data']['answer']}")
        
        print(f"\n📚 來源文檔 ({len(data['data']['sources'])} 個):")
        for i, source in enumerate(data['data']['sources'], 1):
            print(f"  {i}. {source['source']} (相似度: {source['similarity_score']:.3f})")
        
        print(f"\n⚡ 性能:")
        print(f"  延遲: {data['metadata']['latency_ms']}ms")
        if 'token_usage' in data['metadata']:
            usage = data['metadata']['token_usage']
            print(f"  Token使用: {usage['total_tokens']} (prompt: {usage['prompt_tokens']}, completion: {usage['completion_tokens']})")
        
        return True
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"   詳情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"   響應: {e.response.text}")
        return False


def test_api_docs(base_url: str) -> None:
    """顯示 API 文檔鏈接"""
    print("\n" + "=" * 60)
    print("📖 API 文檔")
    print("=" * 60)
    print(f"Swagger UI: {base_url}/docs")
    print(f"ReDoc:      {base_url}/redoc")


def main():
    """主函數"""
    port = sys.argv[1] if len(sys.argv) > 1 else "8000"
    base_url = f"http://127.0.0.1:{port}"
    
    print("\n" + "🚀 " * 20)
    print(f"CourseFlow RAG API 測試")
    print(f"服務地址: {base_url}")
    print("🚀 " * 20)
    
    # 測試健康檢查
    health_ok = test_health(base_url)
    if not health_ok:
        print("\n❌ 健康檢查失敗！請確保服務器正在運行。")
        print(f"\n啟動服務器命令:")
        print(f"  uvicorn src.courseflow.api.main:app --host 127.0.0.1 --port {port} --reload")
        sys.exit(1)
    
    # 測試問答（生物學）
    test_query(
        base_url,
        "What is photosynthesis?",
        "生物學問題"
    )
    
    # 測試問答（編程）
    test_query(
        base_url,
        "How do async functions work in Python?",
        "編程問題"
    )
    
    # 測試問答（數學）
    test_query(
        base_url,
        "What are derivatives in calculus?",
        "數學問題"
    )
    
    # 測試問答（歷史）
    test_query(
        base_url,
        "What caused World War II?",
        "歷史問題"
    )
    
    # 測試無關問題
    print("\n" + "=" * 60)
    print("3️⃣  測試無關問題處理")
    print("=" * 60)
    print(f"❓ 問題: What is the weather today?")
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/query",
            json={"query": "What is the weather today?"},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        print(f"\n✅ 回答: {data['data']['answer']}")
        print(f"📚 來源文檔數: {len(data['data']['sources'])}")
        
    except Exception as e:
        print(f"⚠️  預期行為: 返回「找不到相關資訊」")
    
    # 顯示文檔鏈接
    test_api_docs(base_url)
    
    print("\n" + "✅ " * 20)
    print("所有測試完成！")
    print("✅ " * 20 + "\n")


if __name__ == "__main__":
    main()
