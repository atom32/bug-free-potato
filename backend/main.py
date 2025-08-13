from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import asyncio
from dotenv import load_dotenv

from .agent_core import DeepAgentManager
from .models import ChatRequest, ChatResponse, AgentStatus

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="Deep Agent System",
    description="基于 deepagents 的智能代理系统",
    version="1.0.0"
)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# 初始化 Agent 管理器
agent_manager = DeepAgentManager()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页面"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """处理聊天请求"""
    try:
        response = await agent_manager.process_message(
            message=request.message,
            session_id=request.session_id,
            agent_type=request.agent_type
        )
        return ChatResponse(
            message=response["message"],
            agent_type=response["agent_type"],
            sources=response.get("sources", []),
            session_id=request.session_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/stream/{session_id}")
async def chat_stream(session_id: str, message: str, agent_type: str = "research"):
    """流式聊天响应"""
    async def generate():
        try:
            async for chunk in agent_manager.stream_message(
                message=message,
                session_id=session_id,
                agent_type=agent_type
            ):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/plain")

@app.get("/api/agents/status")
async def get_agent_status():
    """获取代理状态"""
    return await agent_manager.get_status()

@app.post("/api/agents/reset/{session_id}")
async def reset_session(session_id: str):
    """重置会话"""
    await agent_manager.reset_session(session_id)
    return {"message": "会话已重置"}

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "custom_api": os.getenv("CUSTOM_API_BASE_URL"),
        "tavily_configured": bool(os.getenv("TAVILY_API_KEY"))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "True").lower() == "true"
    )