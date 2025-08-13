# DeepAgents 源码设置说明

## 📁 目录结构要求

请确保 deepagents 源码已正确放置在以下位置：

```
deep-agent-system/
└── backend/
    └── deepagents/          # deepagents 源码目录
        ├── __init__.py      # 必需文件
        ├── graph.py         # 必需文件
        ├── model.py         # 必需文件
        ├── state.py         # 必需文件
        ├── sub_agent.py     # 必需文件
        ├── tools.py         # 必需文件
        └── prompts.py       # 必需文件
```

## 🔧 设置步骤

1. **获取 deepagents 源码**
   - 从 deepagents 项目获取源码
   - 或者从你现有的安装中复制源码

2. **放置源码**
   ```bash
   # 创建目录
   mkdir -p backend/deepagents
   
   # 复制源码文件到 backend/deepagents/ 目录
   # 确保包含所有必要的 .py 文件
   ```

3. **验证设置**
   ```bash
   # 运行检查脚本
   python run.py --check
   
   # 或者运行测试
   python test_system.py --quick
   ```

## ✅ 验证清单

确保以下文件存在：
- [ ] `backend/deepagents/__init__.py`
- [ ] `backend/deepagents/graph.py`
- [ ] `backend/deepagents/model.py`
- [ ] `backend/deepagents/state.py`
- [ ] `backend/deepagents/sub_agent.py`
- [ ] `backend/deepagents/tools.py`
- [ ] `backend/deepagents/prompts.py`

## 🚨 常见问题

### 问题 1: 导入错误
```
ImportError: No module named 'deepagents'
```
**解决方案**: 确保 deepagents 源码在正确的位置，并且包含 `__init__.py` 文件。

### 问题 2: 缺少文件
```
❌ deepagents 源码缺少文件: graph.py, model.py
```
**解决方案**: 检查并复制所有必需的源码文件到 `backend/deepagents/` 目录。

### 问题 3: 权限问题
```
PermissionError: [Errno 13] Permission denied
```
**解决方案**: 确保对 `backend/deepagents/` 目录有读写权限。

## 🔄 系统回退机制

如果 deepagents 源码有问题，系统会自动回退到简化模式：
- 仍然可以使用自定义 API 进行对话
- 仍然可以使用 Tavily 搜索功能
- 只是不会使用 deepagents 的高级功能

## 📞 获取帮助

如果遇到问题：
1. 运行 `python test_system.py` 进行诊断
2. 检查控制台输出的错误信息
3. 确认所有依赖已正确安装：`pip install -r requirements.txt`

---

**注意**: 本系统设计为即使 deepagents 不可用也能正常工作，但使用完整的 deepagents 源码可以获得最佳体验。