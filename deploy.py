#!/usr/bin/env python3
"""
Deep Agent System 部署脚本
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, check=True):
    """运行命令"""
    print(f"执行: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"命令执行失败: {result.stderr}")
        sys.exit(1)
    return result

def install_dependencies():
    """安装依赖"""
    print("📦 安装 Python 依赖...")
    run_command("pip install -r requirements.txt")
    print("✓ 依赖安装完成")

def setup_environment():
    """设置环境"""
    print("🔧 设置环境...")
    
    # 创建 .env 文件（如果不存在）
    if not Path(".env").exists():
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            print("✓ 已创建 .env 文件，请配置相关参数")
        else:
            print("❌ 未找到 .env.example 文件")
            return False
    
    return True

def create_systemd_service():
    """创建 systemd 服务文件（Linux）"""
    if sys.platform != "linux":
        print("⚠️  systemd 服务仅支持 Linux 系统")
        return
    
    current_dir = Path.cwd().absolute()
    python_path = sys.executable
    
    service_content = f"""[Unit]
Description=Deep Agent System
After=network.target

[Service]
Type=simple
User={os.getenv('USER', 'www-data')}
WorkingDirectory={current_dir}
Environment=PATH={os.environ.get('PATH')}
ExecStart={python_path} run.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    
    service_file = Path("/etc/systemd/system/deep-agent.service")
    
    try:
        with open(service_file, 'w') as f:
            f.write(service_content)
        
        run_command("sudo systemctl daemon-reload")
        run_command("sudo systemctl enable deep-agent")
        
        print("✓ systemd 服务已创建")
        print("使用以下命令管理服务:")
        print("  启动: sudo systemctl start deep-agent")
        print("  停止: sudo systemctl stop deep-agent")
        print("  状态: sudo systemctl status deep-agent")
        print("  日志: sudo journalctl -u deep-agent -f")
        
    except PermissionError:
        print("❌ 需要 sudo 权限创建 systemd 服务")
        print("请手动创建服务文件或使用 sudo 运行此脚本")

def create_docker_files():
    """创建 Docker 文件"""
    print("🐳 创建 Docker 配置...")
    
    # Dockerfile
    dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "8000"]
"""
    
    # docker-compose.yml
    compose_content = """version: '3.8'

services:
  deep-agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - CUSTOM_API_BASE_URL=${CUSTOM_API_BASE_URL}
      - CUSTOM_API_KEY=${CUSTOM_API_KEY}
      - TAVILY_API_KEY=${TAVILY_API_KEY}
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
"""
    
    # .dockerignore
    dockerignore_content = """__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

.DS_Store
.vscode
.idea
*.swp
*.swo

node_modules
npm-debug.log*
"""
    
    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content)
    
    with open(".dockerignore", "w") as f:
        f.write(dockerignore_content)
    
    print("✓ Docker 文件已创建")
    print("使用以下命令部署:")
    print("  构建: docker-compose build")
    print("  启动: docker-compose up -d")
    print("  停止: docker-compose down")
    print("  日志: docker-compose logs -f")

def create_nginx_config():
    """创建 Nginx 配置"""
    nginx_config = """server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # 替换为你的域名
    
    # SSL 证书配置
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    
    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # 代理到 Deep Agent System
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # 静态文件缓存
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/api/health;
        access_log off;
    }
}
"""
    
    with open("nginx.conf", "w") as f:
        f.write(nginx_config)
    
    print("✓ Nginx 配置已创建")
    print("请根据实际情况修改域名和 SSL 证书路径")

def main():
    print("🚀 Deep Agent System 部署脚本")
    print("=" * 50)
    
    # 检查 Python 版本
    if sys.version_info < (3, 7):
        print("❌ 需要 Python 3.7 或更高版本")
        sys.exit(1)
    
    try:
        # 安装依赖
        install_dependencies()
        
        # 设置环境
        if not setup_environment():
            sys.exit(1)
        
        # 询问部署方式
        print("\n选择部署方式:")
        print("1. 直接运行")
        print("2. systemd 服务 (Linux)")
        print("3. Docker")
        print("4. 创建 Nginx 配置")
        print("5. 全部创建")
        
        choice = input("\n请选择 (1-5): ").strip()
        
        if choice == "1":
            print("✓ 环境已准备就绪")
            print("运行: python run.py")
        
        elif choice == "2":
            create_systemd_service()
        
        elif choice == "3":
            create_docker_files()
        
        elif choice == "4":
            create_nginx_config()
        
        elif choice == "5":
            create_systemd_service()
            create_docker_files()
            create_nginx_config()
        
        else:
            print("❌ 无效选择")
            sys.exit(1)
        
        print("\n" + "=" * 50)
        print("✅ 部署配置完成！")
        print("\n📝 下一步:")
        print("1. 配置 .env 文件中的 API 密钥")
        print("2. 根据选择的部署方式启动服务")
        print("3. 访问 http://localhost:8000 测试")
        
    except KeyboardInterrupt:
        print("\n❌ 部署已取消")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 部署失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()