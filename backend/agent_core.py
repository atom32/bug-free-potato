import os
import sys
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator, Literal
from datetime import datetime
import httpx
from tavily import TavilyClient

# 添加当前目录到 Python 路径，以便导入本地 deepagents
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入本地 deepagents 模块
from deepagents import create_deep_agent, SubAgent

# Tavily 搜索工具 - 参照 research_agent.py 的实现
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search - 完全参照 research_agent.py"""
    search_docs = tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
    return search_docs

class DeepAgentManager:
    """Deep Agent 管理器 - 基于 research_agent.py 的实现"""
    
    def __init__(self):
        self.custom_api_base = os.getenv("CUSTOM_API_BASE_URL")
        self.custom_api_key = os.getenv("CUSTOM_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        
        # 会话管理
        self.sessions: Dict[str, Dict] = {}
        self.stats = {
            "total_requests": 0,
            "active_sessions": 0,
            "last_activity": None
        }
        
        # 初始化代理
        self._setup_agents()
    
    def _setup_agents(self):
        """设置代理配置 - 完全参照 research_agent.py"""
        
        try:
            print("🤖 初始化 Deep Agents...")
            
            # 创建自定义模型来替代默认的 Anthropic 模型
            from langchain_core.language_models.chat_models import BaseChatModel
            from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
            from langchain_core.outputs import ChatResult, ChatGeneration
            from langchain_core.callbacks import CallbackManagerForLLMRun
            from typing import Optional, List, Any
            import httpx
            
            class CustomChatModel(BaseChatModel):
                """自定义 LangChain 兼容的聊天模型"""
                
                def __init__(self, **kwargs):
                    super().__init__(**kwargs)
                    # 使用类变量而不是实例变量来避免 Pydantic 验证问题
                    self._base_url = os.getenv("CUSTOM_API_BASE_URL").rstrip('/')
                    self._api_key = os.getenv("CUSTOM_API_KEY")
                    self._model_name = os.getenv("MODEL_NAME", "Qwen3-235B")
                    self._client = httpx.AsyncClient(timeout=60.0)
                
                @property
                def _llm_type(self) -> str:
                    return "custom_chat_model"
                
                def bind_tools(self, tools, **kwargs):
                    """绑定工具 - LangChain 要求的方法"""
                    # 返回自身，因为我们的模型不需要特殊的工具绑定
                    return self
                
                def _generate(
                    self,
                    messages: List[BaseMessage],
                    stop: Optional[List[str]] = None,
                    run_manager: Optional[CallbackManagerForLLMRun] = None,
                    **kwargs: Any,
                ) -> ChatResult:
                    """同步生成方法"""
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    return loop.run_until_complete(self._agenerate(messages, stop, run_manager, **kwargs))
                
                async def _agenerate(
                    self,
                    messages: List[BaseMessage],
                    stop: Optional[List[str]] = None,
                    run_manager: Optional[CallbackManagerForLLMRun] = None,
                    **kwargs: Any,
                ) -> ChatResult:
                    """异步生成方法"""
                    try:
                        # 转换 LangChain 消息格式为 API 格式
                        formatted_messages = []
                        for msg in messages:
                            if isinstance(msg, HumanMessage):
                                formatted_messages.append({"role": "user", "content": msg.content})
                            elif isinstance(msg, AIMessage):
                                formatted_messages.append({"role": "assistant", "content": msg.content})
                            elif isinstance(msg, SystemMessage):
                                formatted_messages.append({"role": "system", "content": msg.content})
                            else:
                                formatted_messages.append({"role": "user", "content": str(msg.content)})
                        
                        # 调用自定义 API
                        response = await self._client.post(
                            f"{self._base_url}/chat/completions",
                            json={
                                "messages": formatted_messages,
                                "model": self._model_name,
                                "temperature": 0.7,
                                "max_tokens": 2000,
                                "stream": False
                            },
                            headers={
                                "Authorization": f"Bearer {self._api_key}",
                                "Content-Type": "application/json"
                            }
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        content = result["choices"][0]["message"]["content"]
                        
                        # 返回 LangChain 格式的结果
                        message = AIMessage(content=content)
                        generation = ChatGeneration(message=message)
                        return ChatResult(generations=[generation])
                        
                    except Exception as e:
                        print(f"自定义模型调用失败: {e}")
                        # 返回错误消息
                        error_message = AIMessage(content=f"抱歉，生成回答时出现错误：{str(e)}")
                        generation = ChatGeneration(message=error_message)
                        return ChatResult(generations=[generation])
            
            # 创建自定义模型实例
            custom_model = CustomChatModel()
            
            # Sub-agent prompts - 直接从 research_agent.py 复制
            sub_research_prompt = """You are a dedicated researcher. Your job is to conduct research based on the users questions.

Conduct thorough research and then reply to the user with a detailed answer to their question

only your FINAL answer will be passed on to the user. They will have NO knowledge of anything except your final message, so your final report should be your final message!"""

            research_sub_agent = {
                "name": "research-agent",
                "description": "Used to research more in depth questions. Only give this researcher one topic at a time. Do not pass multiple sub questions to this researcher. Instead, you should break down a large topic into the necessary components, and then call multiple research agents in parallel, one for each sub question.",
                "prompt": sub_research_prompt,
                "tools": ["internet_search"]
            }

            sub_critique_prompt = """You are a dedicated editor. You are being tasked to critique a report.

You can find the report at `final_report.md`.

You can find the question/topic for this report at `question.txt`.

The user may ask for specific areas to critique the report in. Respond to the user with a detailed critique of the report. Things that could be improved.

You can use the search tool to search for information, if that will help you critique the report

Do not write to the `final_report.md` yourself.

Things to check:
- Check that each section is appropriately named
- Check that the report is written as you would find in an essay or a textbook - it should be text heavy, do not let it just be a list of bullet points!
- Check that the report is comprehensive. If any paragraphs or sections are short, or missing important details, point it out.
- Check that the article covers key areas of the industry, ensures overall understanding, and does not omit important parts.
- Check that the article deeply analyzes causes, impacts, and trends, providing valuable insights
- Check that the article closely follows the research topic and directly answers questions
- Check that the article has a clear structure, fluent language, and is easy to understand.
"""

            critique_sub_agent = {
                "name": "critique-agent",
                "description": "Used to critique the final report. Give this agent some infomration about how you want it to critique the report.",
                "prompt": sub_critique_prompt,
            }

            # Research instructions - 添加当前时间信息
            current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            research_instructions = f"""You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

IMPORTANT: Current date and time is {current_time} (Beijing Time). When users ask for "today's news", "latest", "recent", or "current" information, they are referring to information from {current_date} or very recent dates. Make sure to search for and prioritize the most recent information available.

The first thing you should do is to write the original user question to `question.txt` so you have a record of it.

Use the research-agent to conduct deep research. It will respond to your questions/topics with a detailed answer.

When you think you enough information to write a final report, write it to `final_report.md`

You can call the critique-agent to get a critique of the final report. After that (if needed) you can do more research and edit the `final_report.md`
You can do this however many times you want until are you satisfied with the result.

Only edit the file once at a time (if you call this tool in parallel, there may be conflicts).

Here are instructions for writing the final report:

<report_instructions>

CRITICAL: Make sure the answer is written in the same language as the human messages! If you make a todo plan - you should note in the plan what language the report should be in so you dont forget!
Note: the language the report should be in is the language the QUESTION is in, not the language/country that the question is ABOUT.

Please create a detailed answer to the overall research brief that:
1. Is well-organized with proper headings (# for title, ## for sections, ### for subsections)
2. Includes specific facts and insights from the research
3. References relevant sources using [Title](URL) format
4. Provides a balanced, thorough analysis. Be as comprehensive as possible, and include all information that is relevant to the overall research question. People are using you for deep research and will expect detailed, comprehensive answers.
5. Includes a "Sources" section at the end with all referenced links

You can structure your report in a number of different ways. Here are some examples:

To answer a question that asks you to compare two things, you might structure your report like this:
1/ intro
2/ overview of topic A
3/ overview of topic B
4/ comparison between A and B
5/ conclusion

To answer a question that asks you to return a list of things, you might only need a single section which is the entire list.
1/ list of things or table of things
Or, you could choose to make each item in the list a separate section in the report. When asked for lists, you don't need an introduction or conclusion.
1/ item 1
2/ item 2
3/ item 3

To answer a question that asks you to summarize a topic, give a report, or give an overview, you might structure your report like this:
1/ overview of topic
2/ concept 1
3/ concept 2
4/ concept 3
5/ conclusion

If you think you can answer the question with a single section, you can do that too!
1/ answer

REMEMBER: Section is a VERY fluid and loose concept. You can structure your report however you think is best, including in ways that are not listed above!
Make sure that your sections are cohesive, and make sense for the reader.

For each section of the report, do the following:
- Use simple, clear language
- Use ## for section title (Markdown format) for each section of the report
- Do NOT ever refer to yourself as the writer of the report. This should be a professional report without any self-referential language. 
- Do not say what you are doing in the report. Just write the report without any commentary from yourself.
- Each section should be as long as necessary to deeply answer the question with the information you have gathered. It is expected that sections will be fairly long and verbose. You are writing a deep research report, and users will expect a thorough answer.
- Use bullet points to list out information when appropriate, but by default, write in paragraph form.

REMEMBER:
The brief and research may be in English, but you need to translate this information to the right language when writing the final answer.
Make sure the final answer report is in the SAME language as the human messages in the message history.

Format the report in clear markdown with proper structure and include source references where appropriate.

<Citation Rules>
- Assign each unique URL a single citation number in your text
- End with ### Sources that lists each source with corresponding numbers
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list regardless of which sources you choose
- Each source should be a separate line item in a list, so that in markdown it is rendered as a list.
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
- Citations are extremely important. Make sure to include these, and pay a lot of attention to getting these right. Users will often use these citations to look into more information.
</Citation Rules>
</report_instructions>

You have access to a few tools.

## `internet_search`

Use this to run an internet search for a given query. You can specify the number of results, the topic, and whether raw content should be included.
"""

            # 创建研究代理 - 完全参照 research_agent.py
            self.research_agent = create_deep_agent(
                [internet_search],
                research_instructions,
                model=custom_model,
                subagents=[critique_sub_agent, research_sub_agent],
            ).with_config({"recursion_limit": 1000})
            
            # 创建评审代理
            critique_instructions = f"""You are a professional editor and reviewer. Your task is to analyze and improve content quality.

IMPORTANT: Current date and time is {current_time} (Beijing Time). When reviewing content, consider the timeliness and relevance of information.

Check the following aspects:
- Content accuracy and completeness
- Logical structure and clarity of arguments
- Fluency of language expression
- Relevance and value of information

Provide constructive improvement suggestions and detailed analysis."""

            self.critique_agent = create_deep_agent(
                [internet_search],
                critique_instructions,
                model=custom_model,
                subagents=[research_sub_agent],
            ).with_config({"recursion_limit": 1000})
            
            # 创建通用代理
            general_instructions = f"""You are a friendly, professional AI assistant. You can answer various questions, provide useful advice and information, help solve problems, and engage in meaningful conversations.

IMPORTANT: Current date and time is {current_time} (Beijing Time). When users ask about "today", "now", "recent", or "latest" information, they are referring to {current_date} or very recent dates.

Please communicate with users in a friendly and professional tone, providing accurate and valuable information."""

            self.general_agent = create_deep_agent(
                [internet_search],
                general_instructions,
                model=custom_model,
            ).with_config({"recursion_limit": 1000})
            
            print("✓ Deep Agents 初始化成功")
            
        except Exception as e:
            print(f"❌ Deep Agents 初始化失败: {e}")
            import traceback
            print(f"错误详情: {traceback.format_exc()}")
            # 如果 deepagents 初始化失败，设置为 None
            self.research_agent = None
            self.critique_agent = None
            self.general_agent = None
    
    async def process_message(self, message: str, session_id: str = "default", agent_type: str = "research") -> Dict[str, Any]:
        """处理消息"""
        self.stats["total_requests"] += 1
        self.stats["last_activity"] = datetime.now().isoformat()
        
        # 确保会话存在
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "created_at": datetime.now().isoformat()
            }
            self.stats["active_sessions"] = len(self.sessions)
        
        try:
            # 选择对应的代理
            agent = None
            if agent_type == "research" and self.research_agent:
                agent = self.research_agent
            elif agent_type == "critique" and self.critique_agent:
                agent = self.critique_agent
            elif agent_type == "general" and self.general_agent:
                agent = self.general_agent
            
            # 如果有可用的 deepagent，使用它
            if agent:
                try:
                    print(f"🤖 使用 Deep Agent ({agent_type}) 处理消息")
                    
                    # 使用 deepagent 处理消息
                    from langchain_core.messages import HumanMessage
                    
                    # 创建初始状态
                    initial_state = {"messages": [HumanMessage(content=message)]}
                    
                    # 调用代理（同步方式，因为 deepagents 可能不支持异步）
                    import asyncio
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, agent.invoke, initial_state)
                    
                    # 提取响应 - 寻找最终的人类可读响应
                    assistant_message = ""
                    if "messages" in result and result["messages"]:
                        # 从后往前查找，寻找最后一个 AI 消息（不是工具调用）
                        for msg in reversed(result["messages"]):
                            if hasattr(msg, 'type') and msg.type == 'ai':
                                # 检查是否是工具调用
                                if not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                                    assistant_message = msg.content
                                    break
                            elif hasattr(msg, 'content') and msg.content and not msg.content.startswith('`'):
                                # 避免返回以 ` 开头的工具调用内容
                                assistant_message = msg.content
                                break
                        
                        # 如果没有找到合适的消息，使用最后一条消息
                        if not assistant_message:
                            last_message = result["messages"][-1]
                            assistant_message = last_message.content
                    else:
                        assistant_message = "代理处理完成，但未返回具体内容。"
                    
                    # 清理响应内容，移除工具调用相关的内容
                    if assistant_message:
                        # 移除 Python 代码块
                        import re
                        assistant_message = re.sub(r'`python[^`]*`', '', assistant_message)
                        # 移除其他代码块
                        assistant_message = re.sub(r'```[^`]*```', '', assistant_message)
                        # 移除单行代码
                        assistant_message = re.sub(r'`[^`]*`', '', assistant_message)
                        # 清理多余的空行
                        assistant_message = re.sub(r'\n\s*\n', '\n\n', assistant_message.strip())
                    
                    # 更新会话历史
                    self.sessions[session_id]["history"].extend([
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": assistant_message}
                    ])
                    
                    return {
                        "message": assistant_message,
                        "agent_type": agent_type,
                        "sources": []
                    }
                    
                except Exception as e:
                    print(f"DeepAgent 处理失败，回退到简化模式: {e}")
                    import traceback
                    print(f"错误详情: {traceback.format_exc()}")
                    # 回退到简化处理
            
            # 简化处理模式（当 deepagents 不可用时）
            messages = [
                {"role": "system", "content": self._get_system_prompt(agent_type)}
            ]
            
            # 添加历史对话
            session_history = self.sessions[session_id]["history"]
            if session_history:
                # 只添加最近的对话历史
                recent_history = session_history[-6:]  # 最近3轮对话（6条消息）
                messages.extend(recent_history)
            
            # 添加当前用户消息
            messages.append({"role": "user", "content": message})
            
            # 如果需要搜索，先进行搜索
            search_results = []
            if any(keyword in message.lower() for keyword in ["搜索", "查找", "研究", "最新", "search", "find"]):
                try:
                    search_results = internet_search(message, max_results=5)
                    print(f"🔍 搜索结果类型: {type(search_results)}, 内容: {search_results}")
                    
                    # 处理搜索结果
                    results_list = []
                    if isinstance(search_results, dict) and "results" in search_results:
                        results_list = search_results["results"]
                    elif isinstance(search_results, list):
                        results_list = search_results
                    
                    if results_list:
                        search_context = "\n".join([
                            f"标题: {result.get('title', '')}\n内容: {result.get('content', '')[:500]}..."
                            for result in results_list[:3]
                            if isinstance(result, dict)
                        ])
                        if search_context:
                            messages.append({
                                "role": "system", 
                                "content": f"搜索结果参考：\n{search_context}"
                            })
                except Exception as e:
                    print(f"搜索过程出错: {e}")
                    search_results = []
            
            # 简化模式下直接返回错误信息
            assistant_message = "抱歉，Deep Agents 未能正确初始化，无法处理您的请求。"
            

            
            # 更新会话历史
            self.sessions[session_id]["history"].extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": assistant_message}
            ])
            
            # 格式化源信息
            sources = []
            try:
                results_list = []
                if isinstance(search_results, dict) and "results" in search_results:
                    results_list = search_results["results"]
                elif isinstance(search_results, list):
                    results_list = search_results
                
                if results_list:
                    sources = [
                        {
                            "title": result.get("title", "") if isinstance(result, dict) else "",
                            "url": result.get("url", "") if isinstance(result, dict) else "",
                            "content": (result.get("content", "")[:200] + "...") if isinstance(result, dict) else ""
                        }
                        for result in results_list[:5]
                        if isinstance(result, dict)
                    ]
            except Exception as e:
                print(f"处理搜索结果时出错: {e}")
                sources = []
            
            return {
                "message": assistant_message,
                "agent_type": agent_type,
                "sources": sources
            }
            
        except Exception as e:
            import traceback
            print(f"处理消息时出错: {e}")
            print(f"错误堆栈: {traceback.format_exc()}")
            return {
                "message": f"抱歉，处理您的请求时出现了错误：{str(e)}",
                "agent_type": agent_type,
                "sources": []
            }
    
    async def stream_message(self, message: str, session_id: str = "default", agent_type: str = "research") -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理消息"""
        try:
            # 先发送开始信号
            yield {"type": "start", "message": "开始处理您的请求..."}
            
            # 如果需要搜索
            if any(keyword in message.lower() for keyword in ["搜索", "查找", "研究", "最新", "search", "find"]):
                yield {"type": "search", "message": "正在搜索相关信息..."}
                search_results = internet_search(message, max_results=5)
                
                # 安全地获取搜索结果数量
                result_count = 0
                try:
                    if isinstance(search_results, dict) and "results" in search_results:
                        result_count = len(search_results["results"])
                    elif isinstance(search_results, list):
                        result_count = len(search_results)
                except:
                    result_count = 0
                
                yield {"type": "search_complete", "message": f"找到 {result_count} 条相关信息"}
            
            # 处理消息
            yield {"type": "thinking", "message": "正在分析和生成回答..."}
            
            result = await self.process_message(message, session_id, agent_type)
            
            # 分块发送响应
            response_text = result["message"]
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield {
                    "type": "content",
                    "message": chunk,
                    "sources": result["sources"] if i == 0 else []
                }
                await asyncio.sleep(0.1)  # 模拟打字效果
            
            yield {"type": "complete", "message": "回答完成"}
            
        except Exception as e:
            yield {"type": "error", "message": f"处理请求时出错：{str(e)}"}
    
    def _get_system_prompt(self, agent_type: str) -> str:
        """获取系统提示"""
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompts = {
            "research": f"""你是一个专业的研究助手。你擅长：
1. 深度研究和分析复杂问题
2. 整合多个信息源提供全面答案
3. 提供准确、详细的信息
4. 用清晰的中文回答问题

重要提示：当前时间是 {current_time}（北京时间）。当用户询问"今日新闻"、"最新"、"近期"或"当前"信息时，他们指的是 {current_date} 或最近几天的信息。请优先搜索和提供最新的信息。

请始终提供有价值、准确的信息，并在可能的情况下引用可靠的来源。""",
            
            "critique": f"""你是一个专业的内容评审员。你的职责是：
1. 分析内容的质量和准确性
2. 提供建设性的改进建议
3. 检查逻辑结构和论证的完整性
4. 确保信息的可靠性和相关性

重要提示：当前时间是 {current_time}（北京时间）。在评审内容时，请考虑信息的时效性和相关性。

请提供详细、客观的评价和改进建议。""",
            
            "general": f"""你是一个友好、专业的AI助手。你可以：
1. 回答各种问题
2. 提供有用的建议和信息
3. 协助解决问题
4. 进行有意义的对话

重要提示：当前时间是 {current_time}（北京时间）。当用户询问"今天"、"现在"、"最近"或"最新"信息时，他们指的是 {current_date} 或最近的时间。

请用友好、专业的语气与用户交流。"""
        }
        
        return prompts.get(agent_type, prompts["general"])
    
    async def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "active_sessions": len(self.sessions),
            "total_requests": self.stats["total_requests"],
            "api_status": {
                "custom_api": bool(self.custom_api_base and self.custom_api_key),
                "tavily_api": bool(self.tavily_api_key)
            },
            "last_activity": self.stats["last_activity"]
        }
    
    async def reset_session(self, session_id: str):
        """重置会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.stats["active_sessions"] = len(self.sessions)