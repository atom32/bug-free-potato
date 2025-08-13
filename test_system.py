#!/usr/bin/env python3
"""
Deep Agent System 测试脚本
"""

import asyncio
import httpx
import json
import time
from pathlib import Path

class SystemTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
    
    async def test_health_check(self):
        """测试健康检查"""
        print("🔍 测试健康检查...")
        try:
            response = await self.client.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 健康检查通过: {data}")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False
    
    async def test_agent_status(self):
        """测试代理状态"""
        print("🤖 测试代理状态...")
        try:
            response = await self.client.get(f"{self.base_url}/api/agents/status")
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 代理状态正常: {data}")
                return True
            else:
                print(f"❌ 代理状态失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 代理状态异常: {e}")
            return False
    
    async def test_chat_api(self):
        """测试聊天 API"""
        print("💬 测试聊天 API...")
        try:
            test_message = {
                "message": "你好，这是一个测试消息",
                "session_id": "test_session",
                "agent_type": "general"
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=test_message
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ 聊天 API 正常: {data.get('message', '')[:100]}...")
                return True
            else:
                print(f"❌ 聊天 API 失败: {response.status_code}")
                print(f"响应: {response.text}")
                return False
        except Exception as e:
            print(f"❌ 聊天 API 异常: {e}")
            return False
    
    async def test_deepagents_source(self):
        """测试 deepagents 源码"""
        print("🤖 测试 deepagents 源码...")
        try:
            import os
            deepagents_path = "backend/deepagents"
            
            if not os.path.exists(deepagents_path):
                print("❌ 未找到 backend/deepagents 目录")
                return False
            
            required_files = ["__init__.py", "graph.py", "model.py", "state.py"]
            missing_files = []
            
            for file in required_files:
                if not os.path.exists(os.path.join(deepagents_path, file)):
                    missing_files.append(file)
            
            if missing_files:
                print(f"❌ deepagents 源码缺少文件: {', '.join(missing_files)}")
                return False
            
            print("✓ deepagents 源码完整")
            return True
            
        except Exception as e:
            print(f"❌ deepagents 源码检查异常: {e}")
            return False
    
    async def test_stream_chat(self):
        """测试流式聊天"""
        print("🌊 测试流式聊天...")
        try:
            url = f"{self.base_url}/api/chat/stream/test_session"
            params = {
                "message": "简单介绍一下人工智能",
                "agent_type": "general"
            }
            
            async with self.client.stream("GET", url, params=params) as response:
                if response.status_code == 200:
                    chunks_received = 0
                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            chunks_received += 1
                            if chunks_received <= 3:  # 只显示前几个块
                                print(f"  收到块: {chunk.strip()[:50]}...")
                    
                    if chunks_received > 0:
                        print(f"✓ 流式聊天正常，收到 {chunks_received} 个数据块")
                        return True
                    else:
                        print("❌ 流式聊天未收到数据")
                        return False
                else:
                    print(f"❌ 流式聊天失败: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ 流式聊天异常: {e}")
            return False
    
    async def test_frontend_access(self):
        """测试前端访问"""
        print("🌐 测试前端访问...")
        try:
            response = await self.client.get(self.base_url)
            if response.status_code == 200:
                content = response.text
                if "Deep Agent System" in content:
                    print("✓ 前端页面正常")
                    return True
                else:
                    print("❌ 前端页面内容异常")
                    return False
            else:
                print(f"❌ 前端访问失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 前端访问异常: {e}")
            return False
    
    async def test_static_files(self):
        """测试静态文件"""
        print("📁 测试静态文件...")
        try:
            # 测试 CSS 文件
            css_response = await self.client.get(f"{self.base_url}/static/css/style.css")
            js_response = await self.client.get(f"{self.base_url}/static/js/app.js")
            
            css_ok = css_response.status_code == 200
            js_ok = js_response.status_code == 200
            
            if css_ok and js_ok:
                print("✓ 静态文件访问正常")
                return True
            else:
                print(f"❌ 静态文件访问失败: CSS={css_response.status_code}, JS={js_response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 静态文件测试异常: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🧪 Deep Agent System 系统测试")
        print("=" * 50)
        
        tests = [
            ("健康检查", self.test_health_check),
            ("deepagents源码", self.test_deepagents_source),
            ("代理状态", self.test_agent_status),
            ("前端访问", self.test_frontend_access),
            ("静态文件", self.test_static_files),
            ("聊天 API", self.test_chat_api),
            ("流式聊天", self.test_stream_chat),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}测试:")
            try:
                result = await test_func()
                if result:
                    passed += 1
                    self.test_results.append((test_name, "PASS", None))
                else:
                    self.test_results.append((test_name, "FAIL", "测试失败"))
            except Exception as e:
                print(f"❌ {test_name}测试异常: {e}")
                self.test_results.append((test_name, "ERROR", str(e)))
        
        print("\n" + "=" * 50)
        print("📊 测试结果汇总:")
        print("=" * 50)
        
        for test_name, status, error in self.test_results:
            status_icon = "✓" if status == "PASS" else "❌"
            print(f"{status_icon} {test_name}: {status}")
            if error:
                print(f"   错误: {error}")
        
        print(f"\n📈 总体结果: {passed}/{total} 测试通过")
        
        if passed == total:
            print("🎉 所有测试通过！系统运行正常")
            return True
        else:
            print("⚠️  部分测试失败，请检查系统配置")
            return False
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Deep Agent System 测试")
    parser.add_argument("--url", default="http://localhost:8000", help="系统 URL")
    parser.add_argument("--quick", action="store_true", help="快速测试（跳过耗时测试）")
    
    args = parser.parse_args()
    
    tester = SystemTester(args.url)
    
    try:
        if args.quick:
            print("⚡ 快速测试模式")
            success = await tester.test_health_check()
            if success:
                success = await tester.test_frontend_access()
        else:
            success = await tester.run_all_tests()
        
        if success:
            print(f"\n🌟 系统测试完成！访问地址: {args.url}")
        else:
            print(f"\n🔧 请检查系统配置并重新测试")
            
    except KeyboardInterrupt:
        print("\n❌ 测试已取消")
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(main())