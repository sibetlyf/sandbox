'use client'

import { useState, useRef, useEffect } from 'react'
import { useWebSocketContext } from '@/hooks/websocket-context'
import { ChatInput } from '@/components/chat/chat-input'
import { ScrollArea } from '@/components/ui/scroll-area' // Using shadcn scroll area
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { AppSidebar } from '@/components/app-sidebar'
import { cn } from '@/lib/utils'
import { Bot, User, FileCode, CheckCircle2, Loader2, Terminal } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { CodeBlock } from '@/components/ai-elements/code-block' // Using V0 code block
import { MessageList } from '@/components/chat/message-list'

import { PreviewPanel } from '@/components/preview-panel'
import { FloatingPanel } from '@/components/floating-panel'
import { FileBrowser } from '@/components/file-browser'
import { FileViewer } from '@/components/file-viewer'
import { IframePreview } from '@/components/iframe-preview'
import { DeployDialog } from '@/components/deploy-dialog'

export default function ChatInterface() {
  const { 
    messages, 
    currentMessage, 
    sendMessage, 
    isProcessing, 
    todoList,
    toolCalls,
    activeFile,
    previewUrl,
    setPreviewUrl,
    floatingPanel,
    setFloatingPanel,
    agentType,
    setAgentType
  } = useWebSocketContext()

  const [input, setInput] = useState('')
  const [mounted, setMounted] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Handle client-side mounting to avoid hydration mismatch
  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    console.log('ChatInterface: messages updated, count:', messages.length, messages);
  }, [messages])

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, currentMessage])

  const handleSubmit = (e: any) => {
    e.preventDefault()
    if (!input.trim()) return
    sendMessage(input)
    setInput('')
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Left Sidebar */}
      <AppSidebar className="w-64 flex-shrink-0 hidden md:block" />

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0 bg-muted/20">
        <div className="flex-1 overflow-y-auto p-4 md:p-8 custom-scrollbar relative">
          <div className="max-w-3xl mx-auto space-y-8 pb-32">
            {messages.length === 0 && !currentMessage && (
                <div className="flex flex-col items-center justify-center h-[50vh] text-center space-y-4">
                    <div className="p-4 rounded-full bg-primary/10">
                        <Bot size={48} className="text-primary" />
                    </div>
                    <h1 className="text-2xl font-bold">How can I help you today?</h1>
                    <p className="text-muted-foreground">Ask me to write code, debug issues, or plan a project.</p>
                </div>
            )}

            <MessageList 
                messages={messages} 
                currentMessage={currentMessage} 
                isProcessing={isProcessing} 
                currentToolCalls={toolCalls}
            />
          </div>
        </div>

        {/* Input Area - Redesigned */}
        <div className="relative border-t bg-gradient-to-b from-background/95 to-background backdrop-blur-sm">
            <div className="max-w-3xl mx-auto p-4 space-y-3">
                {/* Top Action Bar - Agent Selector & Utility Buttons */}
                {mounted && (
                    <div className="flex items-center justify-between gap-3">
                        {/* Agent Selector */}
                        <div className="flex items-center gap-3 px-4 py-2.5 bg-muted/40 hover:bg-muted/60 rounded-xl border border-border/50 transition-all duration-200 shadow-sm hover:shadow-md">
                            <span className={cn(
                                "text-sm font-semibold transition-all duration-200",
                                agentType === 'ccr' ? "text-primary scale-105" : "text-muted-foreground"
                            )}>
                                Claude Code
                            </span>
                            <Switch
                                checked={agentType === 'opencode'}
                                onCheckedChange={(checked) => {
                                    const newType = checked ? 'opencode' : 'ccr';
                                    setAgentType(newType);
                                    localStorage.setItem('vibe_agent_type', newType);
                                }}
                                disabled={isProcessing}
                                className="data-[state=checked]:bg-primary"
                            />
                            <span className={cn(
                                "text-sm font-semibold transition-all duration-200",
                                agentType === 'opencode' ? "text-primary scale-105" : "text-muted-foreground"
                            )}>
                                OpenCode
                            </span>
                            <Badge 
                                variant={agentType === 'ccr' ? "default" : "secondary"} 
                                className="ml-2 text-xs font-bold px-2 py-0.5 shadow-sm"
                            >
                                {agentType === 'ccr' ? 'CCR' : 'OpenCode'}
                            </Badge>
                        </div>

                        {/* Utility Buttons */}
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => setPreviewUrl(process.env.NEXT_PUBLIC_BROWSER_URL || 'about:blank')}
                                className="group px-4 py-2.5 text-sm font-medium text-foreground/80 hover:text-foreground bg-muted/40 hover:bg-muted/70 border border-border/50 rounded-xl transition-all duration-200 flex items-center gap-2 shadow-sm hover:shadow-md hover:scale-105 active:scale-95"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="transition-transform group-hover:rotate-12">
                                    <rect width="18" height="18" x="3" y="3" rx="2"/>
                                    <path d="M9 3v18"/>
                                </svg>
                                <span className="hidden sm:inline">预览</span>
                            </button>
                            <DeployDialog />
                        </div>
                    </div>
                )}
                
                {/* Chat Input */}
                 <ChatInput 
                    message={input} 
                    setMessage={setInput} 
                    onSubmit={handleSubmit} 
                    isLoading={isProcessing}
                    showSuggestions={messages.length === 0}
                 />
            </div>
        </div>
      </main>

      {/* Right Sidebar (Preview or Success/Tasks) */}
      {previewUrl ? (
          <aside className="w-[800px] border-l bg-background shadow-xl flex flex-col transition-all duration-300">
               <PreviewPanel url={previewUrl} onClose={() => setPreviewUrl(null)} />
          </aside>
      ) : (
        <aside className="w-80 border-l bg-muted/30 hidden xl:flex flex-col">
          <div className="p-4 border-b font-semibold flex items-center gap-2">
            <CheckCircle2 size={18} />
            Task Progress
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
                {todoList.length > 0 ? (
                    todoList.map((todo, i) => (
                        <div key={i} className="flex gap-2 items-start text-sm p-2 rounded-md bg-card border">
                           <div className={cn(
                               "mt-0.5 h-4 w-4 rounded-full border flex items-center justify-center shrink-0",
                               todo.status === 'completed' ? "bg-green-500 border-green-500" :
                               todo.status === 'in_progress' ? "border-blue-500" : "border-muted-foreground"
                           )}>
                                {todo.status === 'completed' && <CheckCircle2 size={10} className="text-white" />}
                                {todo.status === 'in_progress' && <Loader2 size={10} className="animate-spin text-blue-500" />}
                           </div>
                           <span className={cn(
                               todo.status === 'completed' && "text-muted-foreground line-through"
                           )}>
                                {todo.content}
                           </span>
                        </div>
                    ))
                ) : (
                    <div className="text-sm text-muted-foreground text-center py-8">
                        No active tasks
                    </div>
                )}
            </div>
          </ScrollArea>
        </aside>
      )}

      {/* Floating Panel */}
      <FloatingPanel
        isOpen={floatingPanel.isOpen}
        onClose={() => setFloatingPanel({ isOpen: false })}
        defaultTab={floatingPanel.activeTab}
      >
        {floatingPanel.activeTab === 'files' ? (
          <div className="flex h-full">
            <div className="w-64 border-r">
              <FileBrowser
                selectedFile={floatingPanel.selectedFile}
                onFileSelect={(path) => setFloatingPanel({ selectedFile: path })}
              />
            </div>
            <div className="flex-1">
              <FileViewer filePath={floatingPanel.selectedFile} />
            </div>
          </div>
        ) : (
          <IframePreview initialUrl={floatingPanel.previewUrl || undefined} />
        )}
      </FloatingPanel>
    </div>
  )
}
