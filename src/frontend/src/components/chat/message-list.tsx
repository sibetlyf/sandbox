'use client'

import React, { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { Message, MessageAvatar } from '@/components/ai-elements/message'
import { Reasoning, ReasoningContent, ReasoningTrigger } from '@/components/ai-elements/reasoning'
import { Tool, ToolContent, ToolHeader, ToolInput, ToolOutput } from '@/components/ai-elements/tool'
import { CodeBlock } from '@/components/ai-elements/code-block'
import { Loader } from '@/components/ai-elements/loader'
import { MessageContent } from '@/components/chat/message-content'
import type { Message as IMessage, ToolCall } from '@/hooks/use-websocket'
import { User, Bot, Clock } from 'lucide-react'

interface MessageListProps {
  messages: IMessage[]
  isProcessing: boolean
  currentMessage: IMessage | null
  currentToolCalls?: ToolCall[]
}

export function MessageList({ messages, isProcessing, currentMessage, currentToolCalls = [] }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Debug logging
  useEffect(() => {
    console.log('MessageList: Received messages:', messages.length, messages);
  }, [messages])

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, currentMessage, isProcessing, currentToolCalls])

  // Helper to render a single message
  const renderMessage = (msg: IMessage, isCurrent = false, index?: number) => {
    const isUser = msg.role === 'user'

    return (
      <Message key={msg.id || index || 'current'} from={msg.role} className={isUser ? "is-user" : "is-assistant"}>
        <MessageAvatar 
            name={isUser ? "User" : "Vibe"} 
            className={isUser ? "bg-muted text-muted-foreground" : "bg-black text-white dark:bg-white dark:text-black shadow-sm"}
        > 
            {!isUser && <Bot className="h-4 w-4" />}
            {isUser && <User className="h-4 w-4" />}
        </MessageAvatar>
        
        <div className="flex-1 space-y-2 overflow-hidden min-w-0">
          <MessageContent message={msg} isCurrent={isCurrent} />
          {msg.timestamp && (
            <div className="text-timestamp flex items-center gap-1.5 text-gray-400 dark:text-gray-500">
              <Clock className="h-3 w-3" />
              <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
            </div>
          )}
        </div>
      </Message>
    )
  }

  return (
    <div className="flex flex-col gap-6 pb-4">
      {messages.map((msg, idx) => renderMessage(msg, false, idx))}
      
      {currentMessage && renderMessage(currentMessage, true)}

      {/* Show active tool calls if they haven't been merged into a message yet */}
      {isProcessing && !currentMessage && currentToolCalls.length > 0 && (
         <Message from="assistant" className="is-assistant">
             <MessageAvatar className="bg-black text-white dark:bg-white dark:text-black shadow-sm">
                 <Bot className="h-4 w-4" />
             </MessageAvatar>
             <div className="flex-1 space-y-4">
                {currentToolCalls.map((tool) => (
                    <Tool key={tool.id}>
                        <ToolHeader type="function" state="input-available" />
                        <ToolContent>
                            <ToolInput input={tool.input} />
                        </ToolContent>
                    </Tool>
                ))}
                <Loader size={20} className="text-muted-foreground opacity-50" />
             </div>
         </Message>
      )}

      {/* Simple Loading Indicator if processing but no current message */}
      {isProcessing && !currentMessage && currentToolCalls.length === 0 && (
         <div className="flex w-full items-start gap-4 py-4 is-assistant">
             <MessageAvatar className="bg-black text-white dark:bg-white dark:text-black shadow-sm">
                 <Bot className="h-4 w-4" />
             </MessageAvatar>
             <Loader size={20} className="mt-2 text-muted-foreground opacity-50" />
         </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
