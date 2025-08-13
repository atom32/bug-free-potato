#!/usr/bin/env python3
"""
Deep Agent System 启动脚本
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_requirements():
    """检查依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import tavily
        import langchain
        import langgraph
        print("✓ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def check_deepagents_source():
    """检查本地 deepagents 源码"""
    deepagents_path = Path("backend/deepagents")
    if not deepagents_path.exists():
        print("✗ 未找到 backend/deepagents 目录")
        print("请确保 deepagents 源码已放置在 backend/deepagents 目录下")
        return False
    
    required_files = ["__init__.py", "graph.py", "model.py", "state.py"]
    missing_files = []
    
    for file in required_files:
        if not (deepagents_path / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"✗ deepagents 源码缺少文件: {', '.join(missing_files)}")
        return False
    
    print("✓ deepagents 源码完整")
    return True

def check_env_file():
    """检查环境变量文件"""
    env_file = Path(".env")
    if not env_file.exists():
        print("✗ 未找到 .env 文件")
        print("请复制 .env.example 为 .env 并配置相关参数")
        return False
    
    # 检查必要的环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ["CUSTOM_API_BASE_URL", "TAVILY_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"✗ 缺少环境变量: {', '.join(missing_vars)}")
        print("请在 .env 文件中配置这些变量")
        return False
    
    print("✓ 环境变量配置正确")
    return True

def create_directories():
    """创建必要的目录"""
    dirs = ["backend", "frontend/static/css", "frontend/static/js", "frontend/templates"]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    print("✓ 目录结构已创建")

def main():
    # 先加载环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Deep Agent System")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="服务器主机地址")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="启用自动重载")
    parser.add_argument("--check", action="store_true", help="仅检查环境")
    
    args = parser.parse_args()
    
    print("🤖 Deep Agent System 启动检查...")
    print("=" * 50)
    
    # 创建目录
    create_directories()
    
    # 检查依赖
    if not check_requirements():
        sys.exit(1)
    
    # 检查 deepagents 源码
    if not check_deepagents_source():
        sys.exit(1)
    
    # 检查环境变量
    if not check_env_file():
        sys.exit(1)
    
    if args.check:
        print("✓ 所有检查通过！")
        return
    
    print("=" * 50)
    print("🚀 启动 Deep Agent System...")
    print(f"📍 地址: http://{args.host}:{args.port}")
    print("=" * 50)
    
    # 启动服务器
    try:
        # 添加当前目录到 Python 路径
        sys.path.insert(0, str(Path.cwd()))
        
        import uvicorn
        uvicorn.run(
            "backend.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Deep Agent System 已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()