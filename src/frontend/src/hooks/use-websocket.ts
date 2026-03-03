import { useState, useEffect, useRef, useCallback } from 'react';

// Configuration


// Helper to get config with precedence: LocalStorage > Env > Default
const getConfig = () => {
    if (typeof window === 'undefined') {
        // Server-side: use env vars directly
        return {
            host: process.env.NEXT_PUBLIC_WS_HOST || 'localhost',
            port: process.env.NEXT_PUBLIC_WS_PORT || '9999',
            password: process.env.NEXT_PUBLIC_WS_PASSWORD || ''
        };
    }
    // Client-side: localStorage > env vars > defaults
    return {
        host: localStorage.getItem('vibe_ws_host') || process.env.NEXT_PUBLIC_WS_HOST || 'localhost',
        port: localStorage.getItem('vibe_ws_port') || process.env.NEXT_PUBLIC_WS_PORT || '9999',
        password: localStorage.getItem('vibe_ws_password') || process.env.NEXT_PUBLIC_WS_PASSWORD || ''
    };
};


const getWsUrl = () => {
    // If server-side, we can't determine window location
    if (typeof window === 'undefined') return '';

    // Use current browser location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    
    // Get password if configured
    const { password } = getConfig();
    const query = password ? `?password=${encodeURIComponent(password)}` : '';
    
    // Connect to Next.js proxy path
    return `${protocol}//${host}/ws/sandbox${query}`;
};

const HEARTBEAT_INTERVAL = 30000;

export interface ToolCall {
    id: string;
    name: string;
    input: any;
}

export interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    thinkingContent?: string;
    toolCalls?: ToolCall[];
    timestamp: string;
    _updateToken?: number;
    todo_list?: any[];
}

export interface WebSocketState {
    isConnected: boolean;
    connectionError: string | null;
    messages: Message[];
    currentMessage: Message | null;
    isProcessing: boolean;
    sendMessage: (prompt: string, options?: any) => void;
    cancelTask: (taskId: string) => void;
    clearMessages: () => void;
    startNewSession: () => void;
    currentSessionId: string | null;
    todoList: any[];
    toolCalls: ToolCall[];
    files: Record<string, any>;
    activeFile: string | null;
    previewUrl: string | null;
    setPreviewUrl: (url: string | null) => void;
    loadSession: (sessionId: string) => void;
    sessions: any[];
    floatingPanel: {
        isOpen: boolean;
        activeTab: 'files' | 'preview';
        selectedFile: string | null;
        previewUrl: string | null;
    };
    setFloatingPanel: (panel: Partial<WebSocketState['floatingPanel']>) => void;
    agentType: 'ccr' | 'opencode';
    setAgentType: (type: 'ccr' | 'opencode') => void;
}

export const useWebSocket = (): WebSocketState => {
    // --- Connection State ---
    const [isConnected, setIsConnected] = useState(false);
    const [connectionError, setConnectionError] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const heartbeatRef = useRef<NodeJS.Timeout | null>(null);

    // --- Data State ---
    const [messages, setMessages] = useState<Message[]>([]);
    const [currentMessage, setCurrentMessage] = useState<Message | null>(null);
    const [isProcessing, setIsProcessing] = useState(false);

    // Auxiliary View State
    const [todoList, setTodoList] = useState<any[]>([]);
    const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
    const [files, setFiles] = useState<Record<string, any>>({});
    const [activeFile, setActiveFile] = useState<string | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [sessions, setSessions] = useState<any[]>([]);
    const [floatingPanel, setFloatingPanelState] = useState({
        isOpen: false,
        activeTab: 'files' as 'files' | 'preview',
        selectedFile: null as string | null,
        previewUrl: null as string | null
    });

    // Session Management - Separate sessions for each agent
    const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

    // Agent Selection - Start with default to avoid hydration mismatch
    const [agentType, setAgentTypeState] = useState<'ccr' | 'opencode'>('ccr');

    // Load from localStorage after mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const savedAgentType = (localStorage.getItem('vibe_agent_type') as 'ccr' | 'opencode') || 'ccr';
            setAgentTypeState(savedAgentType);
            
            const sessionKey = savedAgentType === 'ccr' ? 'vibe_coding_session_id' : 'vibe_opencode_session_id';
            const savedSessionId = localStorage.getItem(sessionKey);
            setCurrentSessionId(savedSessionId);
        }
    }, []);

    // Wrapper to handle agent type changes and session switching
    const setAgentType = useCallback((newType: 'ccr' | 'opencode') => {
        setAgentTypeState(newType);
        localStorage.setItem('vibe_agent_type', newType);
        
        // Switch to the session for the new agent type
        const sessionKey = newType === 'ccr' ? 'vibe_coding_session_id' : 'vibe_opencode_session_id';
        const newSessionId = localStorage.getItem(sessionKey);
        setCurrentSessionId(newSessionId);
        
        // Load history for the new session if it exists
        if (newSessionId) {
            fetchSessionHistory(newSessionId);
        } else {
            // Clear messages when switching to an agent with no session
            setMessages([]);
            setCurrentMessage(null);
            setTodoList([]);
            setToolCalls([]);
        }
    }, []);

    // --- Buffers ---
    const taskBufferRef = useRef<Record<string, any>>({});
    const updatePendingRef = useRef(false);

    // --- Helpers ---
    const serializeTask = useCallback((taskId: string) => {
        const taskData = taskBufferRef.current[taskId];
        if (!taskData) return null;

        const blocks = Object.values(taskData) as any[];

        const combinedText = blocks.map(b => b.text || '').join('');
        const combinedThinking = blocks.map(b => b.thinking || '').join('');
        const allTools = blocks.flatMap(b => b.tools || []);
        
        // Deduplicate tools
        const uniqueTools = Array.from(new Map(allTools.map((t: any) => [t.id, t])).values()) as ToolCall[];

        return {
            id: taskId,
            role: 'assistant' as const,
            content: combinedText,
            thinkingContent: combinedThinking,
            toolCalls: uniqueTools,
            timestamp: new Date().toISOString(),
            _updateToken: Date.now()
        };
    }, []);

    // --- WebSocket Handlers ---
    const handleMessage = useCallback((data: any) => {
        const { type, task_id } = data;

        if (type === 'ping') {
            wsRef.current?.send(JSON.stringify({ type: 'pong' }));
            return;
        }
        if (type === 'pong') return;
        if (type === 'error') {
            console.error("Backend Error:", data.message);
            return;
        }

        if (type === 'task_start') {
            setIsProcessing(true);
            taskBufferRef.current[task_id] = {};
            return;
        }

        if (type === 'chunk') {
            const { parse_data, text_content, thinking_content, has_todo_list, has_write_files, has_tool_calls } = data;
            const uuid = parse_data?.uuid || 'default';

            if (parse_data?.session_id) {
                setCurrentSessionId((prev: string | null) => {
                    if (parse_data.session_id !== prev) {
                        // Save to the correct session key based on agent type
                        const sessionKey = agentType === 'ccr' ? 'vibe_coding_session_id' : 'vibe_opencode_session_id';
                        localStorage.setItem(sessionKey, parse_data.session_id);
                        return parse_data.session_id;
                    }
                    return prev;
                });
            }

            if (!taskBufferRef.current[task_id]) {
                taskBufferRef.current[task_id] = {};
            }
            if (!taskBufferRef.current[task_id][uuid]) {
                taskBufferRef.current[task_id][uuid] = { text: '', thinking: '', tools: [] };
            }

            const block = taskBufferRef.current[task_id][uuid];

            if (text_content !== undefined) {
                block.text = text_content;
                
                // Detect URL for preview (improved regex to avoid markdown formatting)
                // Match http(s):// followed by valid URL characters, excluding markdown symbols
                const urlMatch = text_content.match(/(https?:\/\/[a-zA-Z0-9\-._~:/?#[\]@!$&'()+,;=]+)/);
                if (urlMatch) {
                    // Clean up any trailing markdown characters
                    const cleanUrl = urlMatch[0].replace(/[*_`~]+$/, '');
                    setPreviewUrl((prev: string | null) => prev ? prev : cleanUrl);
                }
            }
            if (thinking_content !== undefined) block.thinking = thinking_content;
            if (parse_data?.tool_calls) {
                const existingIds = new Set(block.tools.map((t: any) => t.id));
                const newTools = parse_data.tool_calls.filter((t: any) => !existingIds.has(t.id));
                block.tools = [...block.tools, ...newTools];
            }

            if (!updatePendingRef.current) {
                updatePendingRef.current = true;
                setTimeout(() => {
                    const liveMessage = serializeTask(task_id);
                    setCurrentMessage(liveMessage);
                    updatePendingRef.current = false;
                }, 100);
            }

            if (parse_data) {
                if (has_todo_list && parse_data.todo_list) {
                    setTodoList((prev: any[]) => {
                        if (parse_data.todo_list.length === 0 && prev.length > 0) return prev;
                        return parse_data.todo_list;
                    });
                }

                if (has_tool_calls && parse_data.tool_calls) {
                    setToolCalls((prev: ToolCall[]) => {
                        const existingIds = new Set(prev.map(tc => tc.id));
                        const newCalls = parse_data.tool_calls.filter((tc: any) => !existingIds.has(tc.id));
                        return [...prev, ...newCalls];
                    });
                }

                if (has_write_files && parse_data.write_files) {
                    setFiles((prev: Record<string, any>) => {
                        const newFiles = JSON.parse(JSON.stringify(prev));
                        parse_data.write_files.forEach((file: any) => {
                            const path = file.file_path;
                            setActiveFile(path.split('/').pop());

                            const parts = path.split('/').filter((p: string) => p);
                            let current = newFiles;
                            for (let i = 0; i < parts.length - 1; i++) {
                                const part = parts[i];
                                if (!current[part] || current[part].type === 'file') {
                                    current[part] = {};
                                }
                                current = current[part];
                            }
                            const fileName = parts[parts.length - 1];
                            current[fileName] = {
                                type: 'file',
                                path: path,
                                content: file.content,
                                timestamp: new Date().toISOString()
                            };
                        });
                        return newFiles;
                    });
                    setTimeout(() => setActiveFile(null), 2000);
                }
            }
        }

        if (type === 'task_complete' || type === 'task_cancelled') {
            setIsProcessing(false);
            const finalMessage = serializeTask(task_id);
            if (finalMessage && type === 'task_complete') {
                setMessages((prev: Message[]) => [...prev, finalMessage]);
            }
            setCurrentMessage(null);
            delete taskBufferRef.current[task_id];
        }
    }, [serializeTask]);

    const sendMessage = useCallback((prompt: string, options: any = {}) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            console.error('WebSocket not connected');
            return;
        }

        const { use_resume = !!currentSessionId, session_id = currentSessionId, agent_type = agentType, task_id } = options;

        setMessages((prev: Message[]) => [...prev, {
            id: Date.now().toString(),
            role: 'user',
            content: prompt,
            timestamp: new Date().toISOString()
        }]);

        setToolCalls([]);

        const payload = {
            type: 'execute',
            prompt,
            use_resume,
            session_id,
            agent_type,
            task_id: task_id || `task_${Date.now()}`
        };

        wsRef.current.send(JSON.stringify(payload));
        setIsProcessing(true);
    }, [currentSessionId, agentType]);

    const cancelTask = useCallback((taskId: string) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'cancel', task_id: taskId }));
        }
    }, []);

    const clearMessages = useCallback(() => {
        setMessages([]);
        setCurrentMessage(null);
        setTodoList([]);
        setToolCalls([]);
        taskBufferRef.current = {};
    }, []);

    const startNewSession = useCallback(() => {
        console.log('Starting new session...');
        setMessages([]);
        setCurrentMessage(null);
        setTodoList([]);
        setToolCalls([]);
        taskBufferRef.current = {};
        setCurrentSessionId(null);
        
        // Remove session for current agent type
        const sessionKey = agentType === 'ccr' ? 'vibe_coding_session_id' : 'vibe_opencode_session_id';
        localStorage.removeItem(sessionKey);
        initialLoadDone.current = false; // Reset the flag
    }, [agentType]);

    // History Fetching
    const fetchSessionHistory = useCallback(async (sessionId: string) => {
        console.log('Fetching history for session:', sessionId);
        try {
            // Use internal proxy processing
            const apiUrl = `/api/sandbox/api/sessions/${sessionId}/history`;
            console.log('History API URL:', apiUrl);

            const response = await fetch(apiUrl);
            if (response.ok) {
                const data = await response.json();
                console.log('History data received:', data);
                if (data.messages && data.messages.length > 0) {
                    console.log('Setting messages, first message:', data.messages[0]);
                    setMessages(data.messages);
                    
                    // Restore latest todo list if available
                    const lastMsg = data.messages[data.messages.length - 1];
                    if (lastMsg?.todo_list) {
                        setTodoList(lastMsg.todo_list);
                    }
                } else {
                    console.log('No messages found in history.');
                    setMessages([]); // Ensure empty array if no messages
                }
            } else {
                console.error('History API error:', response.status, response.statusText);
            }
        } catch (error) {
            console.error('Failed to fetch session history:', error);
        }
    }, []);

    const loadSession = useCallback((sessionId: string) => {
        console.log('Loading session:', sessionId);
        // First, clear everything immediately
        setMessages([]);
        setCurrentMessage(null);
        setTodoList([]);
        setToolCalls([]);
        taskBufferRef.current = {};
        
        // Then set the new session ID
        setCurrentSessionId(sessionId);
        
        // Save to the correct session key based on agent type
        const sessionKey = agentType === 'ccr' ? 'vibe_coding_session_id' : 'vibe_opencode_session_id';
        localStorage.setItem(sessionKey, sessionId);
        
        // Finally, fetch history after a brief delay to ensure state is cleared
        setTimeout(() => {
            fetchSessionHistory(sessionId);
        }, 50);
    }, [fetchSessionHistory, agentType]);

    // Fetch sessions list
    useEffect(() => {
        const fetchSessions = async () => {
            try {
                // Use internal proxy processing
                const response = await fetch(`/api/sandbox/api/sessions`);
                if (response.ok) {
                    const data = await response.json();
                    setSessions(data.sessions || []);
                }
            } catch (error) {
                console.error('Failed to fetch sessions:', error);
            }
        };

        fetchSessions();
        // Refresh sessions periodically
        const interval = setInterval(fetchSessions, 10000);
        return () => clearInterval(interval);
    }, []);

    // Lifecycle
    const handleMessageRef = useRef(handleMessage);
    useEffect(() => {
        handleMessageRef.current = handleMessage;
    }, [handleMessage]);

    // Load history when page first loads (only if session exists)
    const initialLoadDone = useRef(false);
    useEffect(() => {
        if (currentSessionId && isConnected && !initialLoadDone.current) {
            console.log('Initial load: fetching history for current session');
            fetchSessionHistory(currentSessionId);
            initialLoadDone.current = true;
        }
    }, [currentSessionId, isConnected, fetchSessionHistory]);

    useEffect(() => {
        const connect = () => {
            const wsUrl = getWsUrl();
            
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                setIsConnected(true);
                setConnectionError(null);
                if (heartbeatRef.current) clearInterval(heartbeatRef.current);
                heartbeatRef.current = setInterval(() => {
                    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }));
                }, HEARTBEAT_INTERVAL);
            };

            ws.onerror = (error) => {
                console.error("WebSocket error:", error);
                setConnectionError("Connection Failed");
                setIsConnected(false);
            };

            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    handleMessageRef.current(data);
                } catch (err) {
                    console.error('Parse error', err);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                if (heartbeatRef.current) clearInterval(heartbeatRef.current);
                setTimeout(connect, 3000);
            };

            wsRef.current = ws;
        };

        connect();

        return () => {
            if (wsRef.current) wsRef.current.close();
            if (heartbeatRef.current) clearInterval(heartbeatRef.current);
        };
    }, []);

    const setFloatingPanel = useCallback((updates: Partial<typeof floatingPanel>) => {
        setFloatingPanelState((prev: any) => ({ ...prev, ...updates }))
    }, [])

    return {
        isConnected,
        connectionError,
        messages,
        currentMessage,
        isProcessing,
        sendMessage,
        cancelTask,
        clearMessages,
        startNewSession,
        currentSessionId,
        todoList,
        toolCalls,
        files,
        activeFile,
        previewUrl,
        setPreviewUrl,
        loadSession,
        sessions,
        floatingPanel,
        setFloatingPanel,
        agentType,
        setAgentType
    };
};
