#!/bin/bash

echo "🤖 Deep Agent System 启动脚本"
echo "================================"

# 检查 Python 是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python 3.7+"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
if ! python3 -c "import fastapi" &> /dev/null; then
    echo "📥 安装依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 依赖安装失败"
        exit 1
    fi
fi

# 检查 deepagents 源码
if [ ! -d "backend/deepagents" ]; then
    echo "❌ 未找到 backend/deepagents 目录"
    echo "请确保 deepagents 源码已放置在 backend/deepagents 目录下"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件，请配置 API 密钥"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ 已创建 .env 文件，请编辑配置"
    fi
    echo "请编辑 .env 文件配置你的 API 密钥，然后重新运行此脚本"
    exit 1
fi

# 启动系统
echo "🚀 启动 Deep Agent System..."
echo "📍 访问地址: http://localhost:8000"
echo "================================"
python3 run.py