#!/usr/bin/env python3
"""
测试自定义模型 API 调用
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

async def test_custom_api():
    """测试自定义 API 调用"""
    
    base_url = os.getenv("CUSTOM_API_BASE_URL")
    api_key = os.getenv("CUSTOM_API_KEY")
    model_name = os.getenv("MODEL_NAME")
    
    print(f"🔧 测试配置:")
    print(f"   API Base URL: {base_url}")
    print(f"   API Key: {api_key[:20]}..." if api_key else "   API Key: 未设置")
    print(f"   Model Name: {model_name}")
    print()
    
    if not all([base_url, api_key, model_name]):
        print("❌ 环境变量配置不完整")
        return False
    
    try:
        print("🚀 开始测试 API 调用...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                json={
                    "messages": [
                        {"role": "user", "content": "你好，请简单介绍一下你自己"}
                    ],
                    "model": model_name,
                    "temperature": 0.7,
                    "max_tokens": 500,
                    "stream": False
                },
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            print(f"📊 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✅ API 调用成功!")
                print(f"📝 响应内容: {result.get('choices', [{}])[0].get('message', {}).get('content', '无内容')}")
                return True
            else:
                print(f"❌ API 调用失败")
                print(f"📄 错误响应: {response.text}")
                return False
                
    except httpx.TimeoutException:
        print("❌ 请求超时")
        return False
    except httpx.ConnectError as e:
        print(f"❌ 连接错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_custom_api())
    if success:
        print("\n🎉 自定义模型 API 测试通过!")
    else:
        print("\n💥 自定义模型 API 测试失败!")