# Deep Agent System

基于 deepagents 包构建的智能代理系统，集成自定义 API (10.8.8.77:3002/v1) 和 Tavily API，提供强大的研究和分析能力。

## ✨ 特性

- 🤖 **多类型代理**: 研究代理、评审代理、通用代理
- 📦 **本地 deepagents**: 使用本地 deepagents 源码，无需 pip 安装
- 🔍 **智能搜索**: 集成 Tavily API 进行实时网络搜索
- 💬 **流式对话**: 实时流式响应，提供更好的用户体验
- 🎨 **现代界面**: 响应式设计，支持深色主题
- 🔧 **自定义 API**: 集成你的专属 LLM API
- 📱 **移动友好**: 完全响应式设计
- 🎤 **语音输入**: 支持语音转文字输入
- 📊 **系统监控**: 实时系统状态监控

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo>
cd deep-agent-system

# 确保 deepagents 源码已放置在 backend/deepagents 目录下
# 目录结构应该是：
# backend/
#   deepagents/
#     __init__.py
#     graph.py
#     model.py
#     state.py
#     ... (其他源码文件)

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置以下参数：
# CUSTOM_API_BASE_URL=http://10.8.8.77:3002/v1
# CUSTOM_API_KEY=your_api_key_here
# TAVILY_API_KEY=your_tavily_api_key_here
```

### 3. 启动系统

```bash
# 检查环境配置
python run.py --check

# 启动服务器
python run.py

# 或者启用开发模式（自动重载）
python run.py --reload
```

### 4. 访问系统

打开浏览器访问: http://localhost:8000

## 📁 项目结构

```
deep-agent-system/
├── backend/
│   ├── main.py              # FastAPI 主应用
│   ├── agent_core.py        # 代理核心逻辑
│   └── models.py            # 数据模型
├── frontend/
│   ├── templates/
│   │   └── index.html       # 主页面模板
│   └── static/
│       ├── css/
│       │   └── style.css    # 样式文件
│       └── js/
│           └── app.js       # 前端逻辑
├── requirements.txt         # Python 依赖
├── .env.example            # 环境变量模板
├── run.py                  # 启动脚本
└── README.md               # 项目说明
```

## 🔧 API 接口

### 聊天接口

```http
POST /api/chat
Content-Type: application/json

{
    "message": "你的问题",
    "session_id": "session_123",
    "agent_type": "research",
    "max_results": 5,
    "include_sources": true
}
```

### 流式聊天接口

```http
GET /api/chat/stream/{session_id}?message=你的问题&agent_type=research
```

### 系统状态

```http
GET /api/agents/status
```

### 重置会话

```http
POST /api/agents/reset/{session_id}
```

## 🤖 代理类型

### 研究代理 (Research Agent)
- 专门用于深度研究和信息收集
- 自动搜索相关信息
- 提供详细的分析报告
- 包含可靠的信息来源

### 评审代理 (Critique Agent)
- 专门用于内容评审和改进建议
- 分析内容质量和准确性
- 提供建设性的改进意见
- 检查逻辑结构和完整性

### 通用代理 (General Agent)
- 处理各种常规对话和问题
- 提供友好的交互体验
- 适合日常咨询和讨论

## 🎨 界面特性

- **响应式设计**: 适配桌面和移动设备
- **深色主题**: 支持浅色/深色主题切换
- **实时打字效果**: 模拟真实对话体验
- **语音输入**: 支持语音转文字输入
- **消息导出**: 支持聊天记录导出
- **快速问题**: 预设常用问题快速开始

## 🔍 搜索功能

系统集成 Tavily API，提供强大的网络搜索能力：

- **实时搜索**: 获取最新信息
- **多主题支持**: 通用、新闻、金融等
- **智能过滤**: 自动筛选相关内容
- **来源引用**: 提供可靠的信息来源

## ⚙️ 配置选项

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `CUSTOM_API_BASE_URL` | 自定义 API 基础 URL | - |
| `CUSTOM_API_KEY` | 自定义 API 密钥 | - |
| `TAVILY_API_KEY` | Tavily API 密钥 | - |
| `HOST` | 服务器主机地址 | 0.0.0.0 |
| `PORT` | 服务器端口 | 8000 |
| `DEBUG` | 调试模式 | True |

### 用户设置

- **主题**: 浅色/深色/自动
- **字体大小**: 小/中/大
- **自动滚动**: 启用/禁用
- **声音提示**: 启用/禁用

## 🛠️ 开发指南

### 添加新的代理类型

1. 在 `agent_core.py` 中定义新的代理配置
2. 在 `models.py` 中添加对应的枚举值
3. 在前端界面中添加选项

### 自定义工具函数

```python
def custom_tool(param1: str, param2: int = 5):
    """自定义工具函数"""
    # 实现你的逻辑
    return result

# 在代理配置中添加工具
agent_config = {
    "name": "custom-agent",
    "tools": [custom_tool]
}
```

### 扩展前端功能

前端使用原生 JavaScript，可以轻松扩展：

```javascript
class CustomFeature {
    constructor(chatApp) {
        this.chatApp = chatApp;
        this.init();
    }
    
    init() {
        // 初始化自定义功能
    }
}
```

## 🐛 故障排除

### 常见问题

1. **API 连接失败**
   - 检查 API 地址和密钥是否正确
   - 确认网络连接正常

2. **搜索功能不工作**
   - 验证 Tavily API 密钥
   - 检查网络防火墙设置

3. **前端资源加载失败**
   - 确认静态文件路径正确
   - 检查文件权限

### 日志查看

```bash
# 启用详细日志
python run.py --reload --log-level debug
```

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如有问题，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至: [your-email]

---

**Deep Agent System** - 让 AI 研究更简单、更高效！