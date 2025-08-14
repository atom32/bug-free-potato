class DeepAgentChat {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.isTyping = false;
        this.settings = this.loadSettings();
        
        this.initializeElements();
        this.bindEvents();
        this.loadSystemStatus();
        this.applySettings();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11);
    }

    initializeElements() {
        this.chatMessages = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.voiceBtn = document.getElementById('voice-btn');
        this.clearBtn = document.getElementById('clear-chat');
        this.exportBtn = document.getElementById('export-chat');
        this.settingsBtn = document.getElementById('settings-btn');
        this.settingsModal = document.getElementById('settings-modal');
        this.closeSettingsBtn = document.getElementById('close-settings');
        this.typingIndicator = document.getElementById('typing-indicator');
        
        // 快速问题按钮
        this.quickQuestions = document.querySelectorAll('.quick-question');
        
        // 代理类型选择
        this.agentTypeInputs = document.querySelectorAll('input[name="agent-type"]');
    }

    bindEvents() {
        // 发送消息
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                this.sendMessage();
            }
        });

        // 清空聊天
        this.clearBtn.addEventListener('click', () => this.clearChat());
        
        // 导出聊天
        this.exportBtn.addEventListener('click', () => this.exportChat());
        
        // 设置
        this.settingsBtn.addEventListener('click', () => this.showSettings());
        this.closeSettingsBtn.addEventListener('click', () => this.hideSettings());
        
        // 快速问题
        this.quickQuestions.forEach(btn => {
            btn.addEventListener('click', () => {
                const question = btn.dataset.question;
                this.messageInput.value = question;
                this.sendMessage();
            });
        });

        // 语音输入（如果支持）
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            this.voiceBtn.addEventListener('click', () => this.startVoiceInput());
        } else {
            this.voiceBtn.style.display = 'none';
        }

        // 点击模态框外部关闭
        this.settingsModal.addEventListener('click', (e) => {
            if (e.target === this.settingsModal) {
                this.hideSettings();
            }
        });
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        const agentType = document.querySelector('input[name="agent-type"]:checked').value;
        
        // 添加用户消息
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.setTyping(true);

        try {
            // 使用流式API
            await this.sendStreamMessage(message, agentType);
        } catch (error) {
            console.error('发送消息失败:', error);
            this.addMessage('抱歉，发送消息时出现错误。请稍后重试。', 'assistant', 'error');
        } finally {
            this.setTyping(false);
        }
    }

    async sendStreamMessage(message, agentType) {
        const response = await fetch(`/api/chat/stream/${this.sessionId}?message=${encodeURIComponent(message)}&agent_type=${agentType}`);
        
        if (!response.ok) {
            throw new Error('网络请求失败');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        let assistantMessageElement = null;
        let fullMessage = '';
        let sources = [];

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        switch (data.type) {
                            case 'start':
                                assistantMessageElement = this.addMessage('', 'assistant', 'typing');
                                this.updateMessageContent(assistantMessageElement, data.message, 'start');
                                break;
                            
                            case 'agent_selected':
                                this.updateMessageContent(assistantMessageElement, data.message, 'agent-selected');
                                break;
                            
                            case 'search':
                                this.updateMessageContent(assistantMessageElement, data.message, 'searching');
                                break;
                            
                            case 'search_retry':
                                this.updateMessageContent(assistantMessageElement, data.message, 'search-retry');
                                break;
                            
                            case 'search_failed':
                                this.updateMessageContent(assistantMessageElement, data.message, 'search-failed');
                                break;
                            
                            case 'search_complete':
                                this.updateMessageContent(assistantMessageElement, data.message, 'search-complete');
                                break;
                            
                            case 'search_empty':
                                this.updateMessageContent(assistantMessageElement, data.message, 'search-empty');
                                break;
                            
                            case 'analyzing':
                                this.updateMessageContent(assistantMessageElement, data.message, 'analyzing');
                                break;
                            
                            case 'agent_thinking':
                                this.updateMessageContent(assistantMessageElement, data.message, 'agent-thinking');
                                break;
                            
                            case 'processing_complete':
                                this.updateMessageContent(assistantMessageElement, data.message, 'processing-complete');
                                break;
                            
                            case 'generating':
                                this.updateMessageContent(assistantMessageElement, data.message, 'generating');
                                break;
                            
                            case 'content':
                                fullMessage += data.message;
                                if (data.sources && data.sources.length > 0) {
                                    sources = data.sources;
                                }
                                let progressText = data.progress ? ` (${data.progress})` : '';
                                this.updateMessageContent(assistantMessageElement, fullMessage, 'content', progressText);
                                break;
                            
                            case 'agent_error':
                                this.updateMessageContent(assistantMessageElement, data.message, 'agent-error');
                                break;
                            
                            case 'fallback':
                                this.updateMessageContent(assistantMessageElement, data.message, 'fallback');
                                break;
                            
                            case 'complete':
                                this.updateMessageContent(assistantMessageElement, fullMessage, 'complete');
                                if (sources.length > 0) {
                                    this.addSources(assistantMessageElement, sources);
                                }
                                if (data.stats) {
                                    this.showCompletionStats(assistantMessageElement, data.stats);
                                }
                                break;
                            
                            case 'error':
                                this.updateMessageContent(assistantMessageElement, data.message, 'error');
                                break;
                        }
                    } catch (e) {
                        console.error('解析流数据失败:', e);
                    }
                }
            }
        }
    }

    addMessage(content, sender, type = 'normal') {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'flex items-start space-x-3 chat-message';

        const avatar = document.createElement('div');
        avatar.className = 'flex-shrink-0';
        
        const avatarIcon = document.createElement('div');
        avatarIcon.className = `w-8 h-8 rounded-full flex items-center justify-center ${
            sender === 'user' ? 'message-user' : 'bg-indigo-600'
        }`;
        
        const icon = document.createElement('i');
        icon.className = `fas ${sender === 'user' ? 'fa-user' : 'fa-robot'} text-white text-sm`;
        
        avatarIcon.appendChild(icon);
        avatar.appendChild(avatarIcon);

        const messageContent = document.createElement('div');
        messageContent.className = 'flex-1';
        
        const messageBubble = document.createElement('div');
        messageBubble.className = `rounded-lg p-3 ${
            sender === 'user' ? 'message-user text-white' : 'message-assistant'
        }`;
        
        const messageText = document.createElement('div');
        messageText.className = 'message-content';
        
        if (type === 'typing') {
            messageText.innerHTML = '<span class="loading-dots">正在处理</span>';
        } else {
            messageText.innerHTML = this.formatMessage(content);
        }
        
        messageBubble.appendChild(messageText);
        messageContent.appendChild(messageBubble);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }

    updateMessageContent(messageElement, content, type, extra = '') {
        if (!messageElement) return;
        
        const messageText = messageElement.querySelector('.message-content');
        
        switch (type) {
            case 'start':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-robot fa-spin mr-2 text-indigo-600"></i>${content}</div>`;
                break;
            case 'agent-selected':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-check text-green-500 mr-2"></i>${content}</div>`;
                break;
            case 'searching':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-search fa-spin mr-2 text-blue-600"></i>${content}</div>`;
                break;
            case 'search-retry':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-redo fa-spin mr-2 text-yellow-600"></i>${content}</div>`;
                break;
            case 'search-failed':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-exclamation-triangle text-yellow-500 mr-2"></i>${content}</div>`;
                break;
            case 'search-complete':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-check text-green-500 mr-2"></i>${content}</div>`;
                break;
            case 'search-empty':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-info-circle text-blue-500 mr-2"></i>${content}</div>`;
                break;
            case 'analyzing':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-brain fa-pulse mr-2 text-purple-600"></i>${content}</div>`;
                break;
            case 'agent-thinking':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-cog fa-spin mr-2 text-indigo-600"></i>${content}</div>`;
                break;
            case 'processing-complete':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-check text-green-500 mr-2"></i>${content}</div>`;
                break;
            case 'generating':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-pen fa-pulse mr-2 text-green-600"></i>${content}</div>`;
                break;
            case 'content':
                const progressInfo = extra ? `<span class="text-xs text-gray-500 ml-2">${extra}</span>` : '';
                messageText.innerHTML = this.formatMessage(content) + '<span class="typing-animation"></span>' + progressInfo;
                break;
            case 'agent-error':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-exclamation-triangle text-red-500 mr-2"></i>${content}</div>`;
                break;
            case 'fallback':
                messageText.innerHTML = `<div class="status-message"><i class="fas fa-redo text-yellow-600 mr-2"></i>${content}</div>`;
                break;
            case 'complete':
                messageText.innerHTML = this.formatMessage(content);
                break;
            case 'error':
                messageText.innerHTML = `<div class="error-message"><i class="fas fa-exclamation-triangle text-red-500 mr-2"></i>${content}</div>`;
                break;
        }
        
        this.scrollToBottom();
    }

    addSources(messageElement, sources) {
        if (!sources || sources.length === 0) return;
        
        const sourcesDiv = document.createElement('div');
        sourcesDiv.className = 'mt-3 space-y-2';
        
        const sourcesTitle = document.createElement('div');
        sourcesTitle.className = 'text-sm font-medium text-gray-600 mb-2';
        sourcesTitle.innerHTML = '<i class="fas fa-link mr-1"></i>参考来源:';
        sourcesDiv.appendChild(sourcesTitle);
        
        sources.forEach((source, index) => {
            const sourceCard = document.createElement('div');
            sourceCard.className = 'source-card bg-gray-50 border border-gray-200 rounded-md p-3 text-sm';
            
            sourceCard.innerHTML = `
                <div class="font-medium text-gray-800 mb-1">
                    <a href="${source.url}" target="_blank" class="hover:text-indigo-600">
                        ${source.title || `来源 ${index + 1}`}
                        <i class="fas fa-external-link-alt ml-1 text-xs"></i>
                    </a>
                </div>
                <div class="text-gray-600 text-xs">
                    ${source.content || ''}
                </div>
            `;
            
            sourcesDiv.appendChild(sourceCard);
        });
        
        const messageContent = messageElement.querySelector('.message-content').parentElement;
        messageContent.appendChild(sourcesDiv);
    }

    showCompletionStats(messageElement, stats) {
        if (!stats) return;
        
        const statsDiv = document.createElement('div');
        statsDiv.className = 'mt-2 text-xs text-gray-500 border-t border-gray-200 pt-2';
        
        const statsItems = [];
        if (stats.response_length) {
            statsItems.push(`📝 ${stats.response_length} 字符`);
        }
        if (stats.search_results) {
            statsItems.push(`🔍 ${stats.search_results} 个来源`);
        }
        if (stats.agent_type) {
            statsItems.push(`🤖 ${stats.agent_type}`);
        }
        
        if (statsItems.length > 0) {
            statsDiv.innerHTML = `<i class="fas fa-info-circle mr-1"></i>${statsItems.join(' • ')}`;
            const messageContent = messageElement.querySelector('.message-content').parentElement;
            messageContent.appendChild(statsDiv);
        }
    }

    formatMessage(content) {
        if (!content) return '';
        
        try {
            // 配置 marked 选项
            marked.setOptions({
                breaks: true,
                gfm: true,
                sanitize: false,
                highlight: function(code, lang) {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(code, { language: lang }).value;
                        } catch (err) {}
                    }
                    return hljs.highlightAuto(code).value;
                }
            });
            
            // 使用 marked 渲染 Markdown
            let html = marked.parse(content);
            
            // 为链接添加 target="_blank"
            html = html.replace(/<a href/g, '<a target="_blank" rel="noopener noreferrer" href');
            
            // 为表格添加样式
            html = html.replace(/<table>/g, '<table class="table-auto border-collapse border border-gray-300 my-4">');
            html = html.replace(/<th>/g, '<th class="border border-gray-300 px-4 py-2 bg-gray-100 font-semibold">');
            html = html.replace(/<td>/g, '<td class="border border-gray-300 px-4 py-2">');
            
            // 为代码块添加样式
            html = html.replace(/<pre><code/g, '<pre class="bg-gray-100 rounded-lg p-4 overflow-x-auto my-4"><code');
            html = html.replace(/<code>/g, '<code class="bg-gray-100 px-2 py-1 rounded text-sm">');
            
            // 为引用添加样式
            html = html.replace(/<blockquote>/g, '<blockquote class="border-l-4 border-gray-300 pl-4 italic my-4 text-gray-700">');
            
            // 为列表添加样式
            html = html.replace(/<ul>/g, '<ul class="list-disc list-inside my-4 space-y-1">');
            html = html.replace(/<ol>/g, '<ol class="list-decimal list-inside my-4 space-y-1">');
            html = html.replace(/<li>/g, '<li class="ml-4">');
            
            // 为标题添加样式
            html = html.replace(/<h1>/g, '<h1 class="text-2xl font-bold my-4">');
            html = html.replace(/<h2>/g, '<h2 class="text-xl font-bold my-3">');
            html = html.replace(/<h3>/g, '<h3 class="text-lg font-bold my-2">');
            html = html.replace(/<h4>/g, '<h4 class="text-base font-bold my-2">');
            html = html.replace(/<h5>/g, '<h5 class="text-sm font-bold my-2">');
            html = html.replace(/<h6>/g, '<h6 class="text-xs font-bold my-2">');
            
            // 为段落添加间距
            html = html.replace(/<p>/g, '<p class="my-2">');
            
            return html;
        } catch (error) {
            console.error('Markdown 渲染失败:', error);
            // 回退到简单的文本格式化
            return content
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-2 py-1 rounded text-sm">$1</code>')
                .replace(/\n/g, '<br>')
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
        }
    }

    setTyping(isTyping) {
        this.isTyping = isTyping;
        this.sendBtn.disabled = isTyping;
        
        if (isTyping) {
            this.typingIndicator.classList.remove('hidden');
            this.sendBtn.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i>';
        } else {
            this.typingIndicator.classList.add('hidden');
            this.sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
        }
    }

    scrollToBottom() {
        if (this.settings.autoScroll) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    clearChat() {
        if (confirm('确定要清空聊天记录吗？')) {
            this.chatMessages.innerHTML = '';
            this.sessionId = this.generateSessionId();
            
            // 添加欢迎消息
            this.addMessage('你好！我是 Deep Agent 智能助手。我可以帮你进行深度研究、内容分析和各种问题解答。请告诉我你想了解什么？', 'assistant');
        }
    }

    exportChat() {
        const messages = Array.from(this.chatMessages.children).map(msg => {
            const sender = msg.querySelector('.fa-user') ? 'User' : 'Assistant';
            const content = msg.querySelector('.message-content').textContent;
            return `${sender}: ${content}`;
        }).join('\n\n');
        
        const blob = new Blob([messages], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat_export_${new Date().toISOString().slice(0, 10)}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    }

    startVoiceInput() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        recognition.lang = 'zh-CN';
        recognition.continuous = false;
        recognition.interimResults = false;
        
        recognition.onstart = () => {
            this.voiceBtn.innerHTML = '<i class="fas fa-microphone-slash text-red-500"></i>';
        };
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            this.messageInput.value = transcript;
        };
        
        recognition.onend = () => {
            this.voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        };
        
        recognition.onerror = (event) => {
            console.error('语音识别错误:', event.error);
            this.voiceBtn.innerHTML = '<i class="fas fa-microphone"></i>';
        };
        
        recognition.start();
    }

    showSettings() {
        this.settingsModal.classList.remove('hidden');
    }

    hideSettings() {
        this.settingsModal.classList.add('hidden');
    }

    loadSettings() {
        const defaultSettings = {
            theme: 'light',
            fontSize: 'medium',
            autoScroll: true,
            soundEnabled: false
        };
        
        const saved = localStorage.getItem('deepagent_settings');
        return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
    }

    saveSettings() {
        localStorage.setItem('deepagent_settings', JSON.stringify(this.settings));
    }

    applySettings() {
        // 应用主题
        if (this.settings.theme === 'dark') {
            document.body.classList.add('dark');
        }
        
        // 应用字体大小
        const fontSizes = { small: '14px', medium: '16px', large: '18px' };
        document.body.style.fontSize = fontSizes[this.settings.fontSize];
        
        // 更新设置界面
        const themeSelect = document.getElementById('theme-select');
        const fontSizeSelect = document.getElementById('font-size-select');
        const autoScrollCheck = document.getElementById('auto-scroll');
        const soundEnabledCheck = document.getElementById('sound-enabled');
        
        if (themeSelect) themeSelect.value = this.settings.theme;
        if (fontSizeSelect) fontSizeSelect.value = this.settings.fontSize;
        if (autoScrollCheck) autoScrollCheck.checked = this.settings.autoScroll;
        if (soundEnabledCheck) soundEnabledCheck.checked = this.settings.soundEnabled;
        
        // 绑定设置变更事件
        [themeSelect, fontSizeSelect, autoScrollCheck, soundEnabledCheck].forEach(element => {
            if (element) {
                element.addEventListener('change', () => {
                    this.settings.theme = themeSelect.value;
                    this.settings.fontSize = fontSizeSelect.value;
                    this.settings.autoScroll = autoScrollCheck.checked;
                    this.settings.soundEnabled = soundEnabledCheck.checked;
                    
                    this.saveSettings();
                    this.applySettings();
                });
            }
        });
    }

    async loadSystemStatus() {
        try {
            const response = await fetch('/api/agents/status');
            const status = await response.json();
            
            document.getElementById('active-sessions').textContent = status.active_sessions;
            document.getElementById('total-requests').textContent = status.total_requests;
            document.getElementById('custom-api-status').textContent = status.api_status.custom_api ? '✓' : '✗';
            document.getElementById('tavily-api-status').textContent = status.api_status.tavily_api ? '✓' : '✗';
            
            // 更新状态指示器
            const statusText = document.getElementById('status-text');
            if (status.api_status.custom_api && status.api_status.tavily_api) {
                statusText.textContent = '系统正常';
                statusText.className = 'text-sm text-green-600';
            } else {
                statusText.textContent = '部分服务不可用';
                statusText.className = 'text-sm text-yellow-600';
            }
        } catch (error) {
            console.error('加载系统状态失败:', error);
            document.getElementById('status-text').textContent = '连接失败';
            document.getElementById('status-text').className = 'text-sm text-red-600';
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new DeepAgentChat();
});