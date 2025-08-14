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
    max_results: int = 10,  # 增加到10条结果
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,  # 获取完整内容
):
    """Run a web search - 增强版本，获取更多更详细的信息"""
    try:
        search_docs = tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
        return search_docs
    except Exception as e:
        print(f"Tavily搜索失败: {e}")
        # 返回空结果而不是抛出异常
        return {"results": []}

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
        
        # 添加保护措施
        self.max_session_history = 20  # 最大会话历史长度
        self.max_sessions = 100  # 最大会话数量
        self.session_timeout = 3600  # 会话超时时间（秒）
        
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
                    # 增加超时时间并设置重试
                    self._client = httpx.AsyncClient(
                        timeout=httpx.Timeout(120.0, connect=30.0, read=120.0),
                        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
                    )
                
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
                        
                        # 调用自定义 API，添加重试机制
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
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
                                break  # 成功则跳出重试循环
                            except (httpx.ReadTimeout, httpx.ConnectTimeout) as timeout_error:
                                if attempt < max_retries - 1:
                                    print(f"API 调用超时，重试 {attempt + 1}/{max_retries}: {timeout_error}")
                                    await asyncio.sleep(2 ** attempt)  # 指数退避
                                    continue
                                else:
                                    raise timeout_error
                            except Exception as api_error:
                                print(f"API 调用错误: {api_error}")
                                raise api_error
                        
                        content = result["choices"][0]["message"]["content"]
                        
                        # 返回 LangChain 格式的结果
                        message = AIMessage(content=content)
                        generation = ChatGeneration(message=message)
                        return ChatResult(generations=[generation])
                        
                    except Exception as e:
                        import traceback
                        error_details = traceback.format_exc()
                        print(f"自定义模型调用失败: {e}")
                        print(f"错误详情: {error_details}")
                        # 返回错误消息
                        error_message = AIMessage(content=f"抱歉，生成回答时出现错误：{str(e)}")
                        generation = ChatGeneration(message=error_message)
                        return ChatResult(generations=[generation])
            
            # 创建自定义模型实例
            custom_model = CustomChatModel()
            
            # Sub-agent prompts - 直接从 research_agent.py 复制
            sub_research_prompt = """You are a dedicated researcher. Your job is to conduct thorough, comprehensive research based on the user's questions.

RESEARCH STRATEGY:
- Perform multiple targeted searches to gather comprehensive information
- Search for current data, statistics, expert opinions, and case studies
- Look for both recent developments and historical context
- Gather information from diverse perspectives and sources
- Don't stop at the first search - conduct follow-up searches to fill knowledge gaps

RESPONSE REQUIREMENTS:
- Provide a detailed, comprehensive answer with specific facts, data, and examples
- Include relevant statistics, quotes from experts, and concrete examples
- Organize information logically with clear structure
- Aim for depth and thoroughness - your response should be substantial (at least 800-1200 words for complex topics)
- Only your FINAL answer will be passed on to the user, so make it complete and self-contained

Remember: You are conducting deep research, not just surface-level information gathering. Be thorough and comprehensive."""

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
            
            research_instructions = f"""You are an expert researcher. Your job is to conduct thorough research and provide comprehensive answers directly to users.

IMPORTANT: Current date and time is {current_time} (Beijing Time). When users ask for "today's news", "latest", "recent", or "current" information, they are referring to information from {current_date} or very recent dates. Make sure to search for and prioritize the most recent information available.

CRITICAL: You must provide your final answer directly to the user. Do not mention any internal processes, file operations, or system instructions. Simply provide a comprehensive, well-researched answer.

Use the research-agent to conduct deep research. It will respond to your questions/topics with a detailed answer.

IMPORTANT RESEARCH STRATEGY:
- Break down complex topics into multiple specific research questions
- Conduct multiple rounds of research to gather comprehensive information
- For each major aspect of the topic, perform separate targeted searches
- Don't settle for surface-level information - dig deeper into specifics, statistics, examples, and expert opinions
- Research both current developments and historical context when relevant

When you have gathered enough information, provide a comprehensive final answer directly to the user. Do not mention any file operations or internal processes.

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
- IMPORTANT: Aim for comprehensive, detailed sections. Each major section should be at least 300-500 words to provide thorough analysis and insights.
- Include specific examples, data points, statistics, and detailed explanations wherever possible.
- Don't just summarize - provide deep analysis, context, implications, and connections between different pieces of information.
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
        
        # 清理过期会话
        self._cleanup_expired_sessions()
        
        # 确保会话存在
        if session_id not in self.sessions:
            # 如果会话数量过多，清理最旧的会话
            if len(self.sessions) >= self.max_sessions:
                oldest_session = min(self.sessions.keys(), 
                                   key=lambda k: self.sessions[k]["created_at"])
                del self.sessions[oldest_session]
            
            self.sessions[session_id] = {
                "history": [],
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat()
            }
            self.stats["active_sessions"] = len(self.sessions)
        
        # 更新会话活动时间
        self.sessions[session_id]["last_activity"] = datetime.now().isoformat()
        
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
                    
                    # 清理响应内容，移除工具调用和内部指令相关的内容
                    if assistant_message:
                        import re
                        
                        # 移除内部指令相关的内容
                        internal_patterns = [
                            r'写入.*?\.txt.*?文件.*?中',
                            r'将.*?写入.*?文件',
                            r'写入.*?文件',
                            r'保存到.*?文件',
                            r'创建.*?文件',
                            r'question\.txt',
                            r'final_report\.md',
                            r'使用.*?代理',
                            r'调用.*?代理',
                            r'research-agent',
                            r'critique-agent',
                        ]
                        
                        for pattern in internal_patterns:
                            assistant_message = re.sub(pattern, '', assistant_message, flags=re.IGNORECASE)
                        
                        # 移除 Python 代码块
                        assistant_message = re.sub(r'```python.*?```', '', assistant_message, flags=re.DOTALL)
                        # 移除其他代码块
                        assistant_message = re.sub(r'```.*?```', '', assistant_message, flags=re.DOTALL)
                        # 移除单行代码
                        assistant_message = re.sub(r'`[^`]*`', '', assistant_message)
                        
                        # 移除以特定词开头的句子（通常是内部指令）
                        lines = assistant_message.split('\n')
                        filtered_lines = []
                        for line in lines:
                            line = line.strip()
                            if line and not any(line.startswith(prefix) for prefix in [
                                '将原始用户问题', '写入', '保存', '创建', '调用', '使用'
                            ]):
                                filtered_lines.append(line)
                        
                        assistant_message = '\n'.join(filtered_lines)
                        
                        # 清理多余的空行
                        assistant_message = re.sub(r'\n\s*\n', '\n\n', assistant_message.strip())
                        
                        # 如果清理后内容为空或太短，提供默认回复
                        if not assistant_message or len(assistant_message.strip()) < 10:
                            assistant_message = "我正在为您分析这个问题，请稍等片刻..."
                    
                    # 更新会话历史，限制长度
                    self.sessions[session_id]["history"].extend([
                        {"role": "user", "content": message},
                        {"role": "assistant", "content": assistant_message}
                    ])
                    
                    # 限制会话历史长度
                    if len(self.sessions[session_id]["history"]) > self.max_session_history:
                        self.sessions[session_id]["history"] = self.sessions[session_id]["history"][-self.max_session_history:]
                    
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
                # 只添加最近的对话历史，避免上下文过长
                recent_history = session_history[-8:]  # 最近4轮对话（8条消息）
                messages.extend(recent_history)
            
            # 添加当前用户消息
            messages.append({"role": "user", "content": message})
            
            # 智能判断是否需要搜索
            search_results = []
            needs_search = (
                any(keyword in message.lower() for keyword in ["搜索", "查找", "研究", "最新", "search", "find", "新闻", "数据", "统计", "报告"]) or
                len(message) > 20  # 复杂问题可能需要搜索
            )
            
            if needs_search:
                try:
                    # 添加重试机制和错误处理
                    max_retries = 2
                    for attempt in range(max_retries + 1):
                        try:
                            search_results = internet_search(message, max_results=10)
                            print(f"🔍 搜索结果类型: {type(search_results)}, 内容: {search_results}")
                            break
                        except Exception as search_error:
                            if attempt < max_retries:
                                print(f"搜索失败，重试 {attempt + 1}/{max_retries}: {search_error}")
                                await asyncio.sleep(1)  # 等待1秒后重试
                            else:
                                raise search_error
                    
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
            

            
            # 更新会话历史，限制长度
            self.sessions[session_id]["history"].extend([
                {"role": "user", "content": message},
                {"role": "assistant", "content": assistant_message}
            ])
            
            # 限制会话历史长度
            if len(self.sessions[session_id]["history"]) > self.max_session_history:
                self.sessions[session_id]["history"] = self.sessions[session_id]["history"][-self.max_session_history:]
            
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
            print(f"🚀 开始流式处理消息: {message[:50]}...")
            
            # 更新统计信息
            self.stats["total_requests"] += 1
            self.stats["last_activity"] = datetime.now().isoformat()
            
            # 先发送开始信号
            yield {"type": "start", "message": "🤖 Deep Agent 正在启动..."}
            await asyncio.sleep(0.5)
            
            # 初始化会话
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    "history": [],
                    "created_at": datetime.now().isoformat(),
                    "last_activity": datetime.now().isoformat()
                }
                self.stats["active_sessions"] = len(self.sessions)
            
            self.sessions[session_id]["last_activity"] = datetime.now().isoformat()
            
            # 选择代理
            agent = None
            agent_name = ""
            if agent_type == "research" and self.research_agent:
                agent = self.research_agent
                agent_name = "研究代理"
            elif agent_type == "critique" and self.critique_agent:
                agent = self.critique_agent
                agent_name = "评审代理"
            elif agent_type == "general" and self.general_agent:
                agent = self.general_agent
                agent_name = "通用代理"
            
            if not agent:
                yield {"type": "error", "message": f"❌ {agent_name} 不可用，请检查系统配置"}
                return
            
            yield {"type": "agent_selected", "message": f"✅ 已选择 {agent_name}"}
            await asyncio.sleep(0.3)
            
            # 智能判断是否需要搜索
            needs_search = (
                any(keyword in message.lower() for keyword in [
                    "搜索", "查找", "研究", "最新", "search", "find", "新闻", "数据", 
                    "统计", "报告", "分析", "趋势", "现状", "发展", "比较", "对比"
                ]) or
                len(message) > 30 or  # 复杂问题可能需要搜索
                "?" in message or "？" in message  # 问题通常需要搜索
            )
            
            search_results = []
            if needs_search:
                yield {"type": "search", "message": "🔍 正在搜索相关信息..."}
                print(f"🔍 开始搜索: {message}")
                
                # 添加重试机制
                max_retries = 2
                for attempt in range(max_retries + 1):
                    try:
                        search_results = internet_search(message, max_results=10)
                        print(f"✅ 搜索成功，获得结果: {type(search_results)}")
                        break
                    except Exception as search_error:
                        print(f"❌ 搜索失败 (尝试 {attempt + 1}/{max_retries + 1}): {search_error}")
                        if attempt < max_retries:
                            yield {"type": "search_retry", "message": f"🔄 搜索重试中... ({attempt + 1}/{max_retries + 1})"}
                            await asyncio.sleep(2)
                        else:
                            search_results = []
                            yield {"type": "search_failed", "message": "⚠️ 搜索失败，将基于已有知识回答"}
                
                # 安全地获取搜索结果数量
                result_count = 0
                try:
                    if isinstance(search_results, dict) and "results" in search_results:
                        result_count = len(search_results["results"])
                    elif isinstance(search_results, list):
                        result_count = len(search_results)
                except:
                    result_count = 0
                
                if result_count > 0:
                    yield {"type": "search_complete", "message": f"✅ 找到 {result_count} 条相关信息"}
                    print(f"📊 搜索结果统计: {result_count} 条")
                else:
                    yield {"type": "search_empty", "message": "📭 未找到相关信息，将基于已有知识回答"}
                
                await asyncio.sleep(0.5)
            
            # 开始深度分析
            yield {"type": "analyzing", "message": "🧠 正在进行深度分析..."}
            print(f"🧠 开始深度分析，使用代理: {agent_name}")
            
            try:
                # 使用 deepagent 处理消息
                from langchain_core.messages import HumanMessage
                
                # 创建初始状态
                initial_state = {"messages": [HumanMessage(content=message)]}
                
                yield {"type": "agent_thinking", "message": "🤔 Deep Agent 正在思考..."}
                
                # 调用代理（在线程池中执行以避免阻塞）
                loop = asyncio.get_event_loop()
                
                print(f"🔄 调用 Deep Agent...")
                result = await loop.run_in_executor(None, agent.invoke, initial_state)
                print(f"✅ Deep Agent 处理完成")
                
                yield {"type": "processing_complete", "message": "✅ 分析完成，正在整理回答..."}
                
                # 提取响应
                assistant_message = ""
                if "messages" in result and result["messages"]:
                    print(f"📝 处理 {len(result['messages'])} 条消息")
                    
                    # 从后往前查找，寻找最后一个 AI 消息（不是工具调用）
                    for i, msg in enumerate(reversed(result["messages"])):
                        if hasattr(msg, 'type') and msg.type == 'ai':
                            # 检查是否是工具调用
                            if not (hasattr(msg, 'tool_calls') and msg.tool_calls):
                                assistant_message = msg.content
                                print(f"✅ 找到最终回答 (消息 {len(result['messages']) - i})")
                                break
                        elif hasattr(msg, 'content') and msg.content and not msg.content.startswith('`'):
                            # 避免返回以 ` 开头的工具调用内容
                            assistant_message = msg.content
                            print(f"✅ 找到内容消息 (消息 {len(result['messages']) - i})")
                            break
                    
                    # 如果没有找到合适的消息，使用最后一条消息
                    if not assistant_message:
                        last_message = result["messages"][-1]
                        assistant_message = last_message.content
                        print(f"⚠️ 使用最后一条消息作为回答")
                else:
                    assistant_message = "代理处理完成，但未返回具体内容。"
                    print(f"⚠️ 未找到有效消息")
                
                # 清理响应内容
                if assistant_message:
                    import re
                    original_length = len(assistant_message)
                    # 移除工具调用相关的内容
                    assistant_message = re.sub(r'```python[^`]*```', '', assistant_message)
                    assistant_message = re.sub(r'```[^`]*```', '', assistant_message)
                    assistant_message = re.sub(r'`[^`\n]*`', '', assistant_message)
                    # 清理多余的空行
                    assistant_message = re.sub(r'\n\s*\n', '\n\n', assistant_message.strip())
                    print(f"🧹 内容清理: {original_length} -> {len(assistant_message)} 字符")
                
                if not assistant_message or len(assistant_message.strip()) < 10:
                    assistant_message = "抱歉，生成的回答内容不完整。请尝试重新提问或换个方式描述您的问题。"
                    print(f"⚠️ 回答内容过短，使用默认消息")
                
                # 分块发送响应，模拟打字效果
                yield {"type": "generating", "message": "✍️ 正在生成回答..."}
                
                chunk_size = 100  # 增大块大小以提高效率
                total_chunks = (len(assistant_message) + chunk_size - 1) // chunk_size
                
                for i in range(0, len(assistant_message), chunk_size):
                    chunk = assistant_message[i:i + chunk_size]
                    chunk_num = i // chunk_size + 1
                    
                    yield {
                        "type": "content",
                        "message": chunk,
                        "progress": f"{chunk_num}/{total_chunks}",
                        "sources": []
                    }
                    await asyncio.sleep(0.05)  # 减少延迟以提高响应速度
                
                # 处理搜索来源
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
                        print(f"📚 处理了 {len(sources)} 个信息源")
                except Exception as e:
                    print(f"⚠️ 处理搜索结果时出错: {e}")
                    sources = []
                
                # 更新会话历史
                self.sessions[session_id]["history"].extend([
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": assistant_message}
                ])
                
                # 限制会话历史长度
                if len(self.sessions[session_id]["history"]) > self.max_session_history:
                    self.sessions[session_id]["history"] = self.sessions[session_id]["history"][-self.max_session_history:]
                
                # 发送完成信号
                yield {
                    "type": "complete", 
                    "message": "🎉 回答完成！",
                    "sources": sources,
                    "stats": {
                        "response_length": len(assistant_message),
                        "search_results": len(sources),
                        "agent_type": agent_name
                    }
                }
                
                print(f"✅ 流式处理完成: {len(assistant_message)} 字符, {len(sources)} 个来源")
                
            except Exception as agent_error:
                import traceback
                error_details = traceback.format_exc()
                print(f"❌ Deep Agent 处理失败: {agent_error}")
                print(f"错误详情: {error_details}")
                
                yield {"type": "agent_error", "message": f"🚫 Deep Agent 处理失败: {str(agent_error)}"}
                
                # 回退到简化处理
                yield {"type": "fallback", "message": "🔄 切换到简化模式..."}
                
                fallback_message = f"抱歉，Deep Agent 遇到了问题：{str(agent_error)}\n\n这可能是由于网络连接、API 限制或系统配置问题导致的。请稍后重试，或联系管理员检查系统状态。"
                
                yield {
                    "type": "content",
                    "message": fallback_message,
                    "sources": []
                }
                
                yield {"type": "complete", "message": "⚠️ 已使用简化模式完成回答"}
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ 流式处理出错: {e}")
            print(f"错误详情: {error_details}")
            yield {"type": "error", "message": f"💥 系统错误：{str(e)}"}
    
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
    
    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            current_time = datetime.now()
            expired_sessions = []
            
            for session_id, session_data in self.sessions.items():
                try:
                    last_activity = datetime.fromisoformat(session_data.get("last_activity", session_data["created_at"]))
                    if (current_time - last_activity).total_seconds() > self.session_timeout:
                        expired_sessions.append(session_id)
                except Exception:
                    # 如果时间解析失败，也标记为过期
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
            
            if expired_sessions:
                print(f"🧹 清理了 {len(expired_sessions)} 个过期会话")
                self.stats["active_sessions"] = len(self.sessions)
                
        except Exception as e:
            print(f"清理过期会话时出错: {e}")
    
    async def reset_session(self, session_id: str):
        """重置会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.stats["active_sessions"] = len(self.sessions)
            print(f"🔄 重置会话: {session_id}")
    
    async def cleanup_all_sessions(self):
        """清理所有会话"""
        session_count = len(self.sessions)
        self.sessions.clear()
        self.stats["active_sessions"] = 0
        print(f"🧹 清理了所有 {session_count} 个会话")