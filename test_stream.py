#!/usr/bin/env python3
"""
测试流式处理改进
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.agent_core import DeepAgentManager

async def test_stream():
    """测试流式处理"""
    print("🧪 测试流式处理改进...")
    
    # 初始化管理器
    manager = DeepAgentManager()
    
    # 测试消息
    test_message = "请简单介绍一下人工智能的发展历史"
    
    print(f"📝 测试消息: {test_message}")
    print("=" * 50)
    
    try:
        async for chunk in manager.stream_message(test_message, "test_session", "research"):
            print(f"📦 [{chunk['type']}] {chunk['message']}")
            
            if chunk['type'] == 'complete':
                if 'stats' in chunk:
                    print(f"📊 统计信息: {chunk['stats']}")
                if 'sources' in chunk and chunk['sources']:
                    print(f"🔗 来源数量: {len(chunk['sources'])}")
                break
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_stream())