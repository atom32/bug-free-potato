from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

class AgentType(str, Enum):
    RESEARCH = "research"
    CRITIQUE = "critique"
    GENERAL = "general"

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    agent_type: AgentType = AgentType.RESEARCH
    max_results: Optional[int] = 5
    include_sources: Optional[bool] = True

class ChatResponse(BaseModel):
    message: str
    agent_type: str
    sources: List[Dict[str, Any]] = []
    session_id: str
    timestamp: Optional[str] = None

class AgentStatus(BaseModel):
    active_sessions: int
    total_requests: int
    api_status: Dict[str, bool]
    last_activity: Optional[str] = None

class SearchResult(BaseModel):
    title: str
    url: str
    content: str
    score: Optional[float] = None