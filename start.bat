@echo off
echo 🤖 Deep Agent System 启动脚本
echo ================================

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.7+
    pause
    exit /b 1
)

REM 检查依赖
echo 📦 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 📥 安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ 依赖安装失败
        pause
        exit /b 1
    )
)

REM 检查 deepagents 源码
if not exist backend\deepagents (
    echo ❌ 未找到 backend\deepagents 目录
    echo 请确保 deepagents 源码已放置在 backend\deepagents 目录下
    pause
    exit /b 1
)

REM 检查环境变量文件
if not exist .env (
    echo ⚠️  未找到 .env 文件，请配置 API 密钥
    if exist .env.example (
        copy .env.example .env
        echo ✓ 已创建 .env 文件，请编辑配置
    )
    echo 请编辑 .env 文件配置你的 API 密钥，然后重新运行此脚本
    pause
    exit /b 1
)

REM 启动系统
echo 🚀 启动 Deep Agent System...
echo 📍 访问地址: http://localhost:8000
echo ================================
python run.py

pause