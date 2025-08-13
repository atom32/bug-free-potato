# Deep Agent System - 项目概览

## 🎯 项目目标

基于 deepagents 源码快速构建一个"到手即用"的 Deep Agent 系统，集成：
- 本地 deepagents 源码（无需 pip 安装）
- 自定义 API (10.8.8.77:3002/v1)
- Tavily API 搜索功能
- 现代化的前后端界面

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   FastAPI       │    │   Deep Agents   │
│   (HTML/JS)     │◄──►│   后端服务      │◄──►│   核心逻辑      │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  自定义 LLM API │    │   Tavily 搜索   │
                       │ (10.8.8.77:3002)│    │      API        │
                       └─────────────────┘    └─────────────────┘
```

## 📁 文件结构

```
deep-agent-system/
├── 🚀 启动文件
│   ├── run.py              # 主启动脚本
│   ├── start.bat           # Windows 快速启动
│   ├── start.sh            # Linux/Mac 快速启动
│   └── deploy.py           # 部署脚本
│
├── ⚙️ 配置文件
│   ├── requirements.txt    # Python 依赖
│   ├── .env               # 环境变量配置
│   └── .env.example       # 环境变量模板
│
├── 🔧 后端代码
│   ├── backend/
│   │   ├── main.py        # FastAPI 主应用
│   │   ├── agent_core.py  # Deep Agent 核心逻辑
│   │   ├── models.py      # 数据模型定义
│   │   └── deepagents/    # deepagents 源码目录
│   │       ├── __init__.py
│   │       ├── graph.py
│   │       ├── model.py
│   │       └── ... (其他源码文件)
│
├── 🎨 前端代码
│   └── frontend/
│       ├── templates/
│       │   └── index.html # 主页面模板
│       └── static/
│           ├── css/
│           │   └── style.css  # 样式文件
│           └── js/
│               └── app.js     # 前端逻辑
│
├── 🧪 测试和文档
│   ├── test_system.py     # 系统测试脚本
│   ├── README.md          # 详细说明文档
│   └── PROJECT_OVERVIEW.md # 项目概览（本文件）
│
└── 🐳 部署配置（运行 deploy.py 生成）
    ├── Dockerfile         # Docker 镜像配置
    ├── docker-compose.yml # Docker Compose 配置
    └── nginx.conf         # Nginx 反向代理配置
```

## 🚀 快速开始

### 方法一：一键启动（推荐）

**Windows:**
```cmd
# 双击运行或在命令行执行
start.bat
```

**Linux/Mac:**
```bash
# 给脚本执行权限并运行
chmod +x start.sh
./start.sh
```

### 方法二：手动启动

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   ```bash
   # 复制配置模板
   cp .env.example .env
   
   # 编辑 .env 文件，配置你的 API 密钥
   # CUSTOM_API_BASE_URL=http://10.8.8.77:3002/v1
   # CUSTOM_API_KEY=your_api_key_here
   # TAVILY_API_KEY=your_tavily_api_key_here
   ```

3. **启动系统**
   ```bash
   python run.py
   ```

4. **访问系统**
   ```
   http://localhost:8000
   ```

## 🔧 核心功能

### 1. 多类型智能代理
- **研究代理**: 深度研究和信息收集
- **评审代理**: 内容评审和改进建议  
- **通用代理**: 日常对话和问题解答

### 2. 智能搜索集成
- 实时网络搜索（Tavily API）
- 自动信息筛选和整合
- 可靠来源引用

### 3. 现代化界面
- 响应式设计，支持移动端
- 实时流式对话体验
- 深色/浅色主题切换
- 语音输入支持

### 4. 强大的后端
- FastAPI 高性能框架
- 异步处理和流式响应
- 会话管理和状态监控
- RESTful API 设计

## 🔌 API 集成

### 自定义 LLM API
```python
# 配置你的 API 端点
CUSTOM_API_BASE_URL = "http://10.8.8.77:3002/v1"
CUSTOM_API_KEY = "your_api_key"

# 系统会自动调用你的 API 进行对话
```

### Tavily 搜索 API
```python
# 配置 Tavily API
TAVILY_API_KEY = "your_tavily_key"

# 自动触发搜索的关键词
search_keywords = ["搜索", "查找", "研究", "最新", "search", "find"]
```

## 🎨 界面特色

### 主要特性
- 🎯 **直观操作**: 简洁的聊天界面，易于使用
- ⚡ **实时响应**: 流式对话，打字机效果
- 📱 **移动友好**: 完全响应式设计
- 🎤 **语音输入**: 支持语音转文字
- 🌙 **主题切换**: 浅色/深色主题
- 📊 **状态监控**: 实时系统状态显示

### 快速功能
- 预设常用问题快速开始
- 一键清空聊天记录
- 聊天记录导出功能
- 代理类型快速切换

## 🧪 测试验证

运行系统测试：
```bash
# 完整测试
python test_system.py

# 快速测试
python test_system.py --quick

# 测试指定 URL
python test_system.py --url http://your-domain.com
```

测试项目包括：
- ✅ 健康检查
- ✅ 代理状态
- ✅ 前端访问
- ✅ 静态文件
- ✅ 聊天 API
- ✅ 流式对话

## 🚀 部署选项

运行部署脚本选择部署方式：
```bash
python deploy.py
```

支持的部署方式：
1. **直接运行**: 开发和测试环境
2. **systemd 服务**: Linux 生产环境
3. **Docker**: 容器化部署
4. **Nginx**: 反向代理配置

## 📈 性能特点

- **高并发**: FastAPI + 异步处理
- **低延迟**: 流式响应，实时交互
- **可扩展**: 模块化设计，易于扩展
- **稳定性**: 错误处理和自动重试

## 🔒 安全考虑

- API 密钥环境变量管理
- HTTPS 支持（Nginx 配置）
- 输入验证和错误处理
- 会话隔离和数据保护

## 🎯 使用场景

### 研究和分析
- 学术研究辅助
- 市场分析报告
- 技术调研总结
- 行业趋势分析

### 内容创作
- 文章写作辅助
- 内容质量评审
- 创意灵感生成
- 多语言翻译

### 日常助手
- 问题解答
- 学习辅导
- 决策支持
- 信息查询

## 🔮 扩展可能

### 功能扩展
- 多模态支持（图片、文档）
- 知识库集成
- 工作流自动化
- 团队协作功能

### 技术扩展
- 更多 LLM 模型支持
- 插件系统
- API 网关集成
- 微服务架构

## 📞 技术支持

如遇问题，请检查：
1. 环境变量配置是否正确
2. API 密钥是否有效
3. 网络连接是否正常
4. 依赖是否完整安装

运行测试脚本诊断问题：
```bash
python test_system.py --quick
```

---

**Deep Agent System** - 让 AI 研究更简单、更高效！🚀