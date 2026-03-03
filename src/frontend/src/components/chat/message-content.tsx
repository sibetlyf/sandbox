'use client'

import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Reasoning, ReasoningContent, ReasoningTrigger } from '@/components/ai-elements/reasoning'
import { Tool, ToolContent, ToolHeader, ToolInput, ToolOutput } from '@/components/ai-elements/tool'
import { CodeBlock } from '@/components/ai-elements/code-block'
import { Wrench, CheckCircle2, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { useWebSocketContext } from '@/hooks/websocket-context'

interface MessageContentProps {
  message: any
  isCurrent?: boolean
}

export function MessageContent({ message, isCurrent = false }: MessageContentProps) {
  const [expandedTools, setExpandedTools] = React.useState<Set<number>>(new Set());
  const { setPreviewUrl } = useWebSocketContext();

  const toggleTool = (index: number) => {
    setExpandedTools(prev => {
      const newSet = new Set(prev);
      if (newSet.has(index)) {
        newSet.delete(index);
      } else {
        newSet.add(index);
      }
      return newSet;
    });
  };

  // Custom link component for ReactMarkdown
  const LinkComponent = ({ href, children, ...props }: any) => {
    const handleClick = (e: React.MouseEvent) => {
      e.preventDefault();
      if (href) {
        setPreviewUrl(href);
      }
    };

    return (
      <a
        href={href}
        onClick={handleClick}
        className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline decoration-blue-400/50 hover:decoration-blue-600 transition-colors cursor-pointer group"
        {...props}
      >
        {children}
        <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
      </a>
    );
  };

  // If message has original content array, render in single flow (V0 style)
  if (message?.message?.content && Array.isArray(message.message.content)) {
    const content = message.message.content;

    return (
      <div className="space-y-4">
        {content.map((item: any, idx: number) => {
          // Thinking block
          if (item.type === 'thinking') {
            return (
              <Reasoning key={idx} defaultOpen={isCurrent} isStreaming={isCurrent}>
                <ReasoningTrigger />
                <ReasoningContent>{item.thinking}</ReasoningContent>
              </Reasoning>
            );
          } 
          // Text block
          else if (item.type === 'text') {
            return (
              <div key={idx} className="prose dark:prose-invert prose-p:leading-relaxed prose-pre:p-0 w-full max-w-none break-words whitespace-pre-wrap">
                <ReactMarkdown 
                  components={{
                      a: LinkComponent,
                      code({ node, className, children, ...props }) {
                          const match = /language-(\w+)/.exec(className || '')
                          const isInline = !match
                          return !isInline ? (
                          <CodeBlock
                              language={match![1]}
                              code={String(children).replace(/\n$/, '')}
                              className="my-4"
                          />
                          ) : (
                          <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-sm" {...props}>
                              {children}
                          </code>
                          )
                      }
                  }}
                >
                  {item.text}
                </ReactMarkdown>
              </div>
            );
          }
          // Tool use block - V0 style with gradients and time stats
          else if (item.type === 'tool_use') {
            const isExpanded = expandedTools.has(idx);
            return (
              <div key={idx} className="my-2 group">
                <div className="relative border border-blue-500/50 dark:border-blue-400/50 rounded-lg overflow-hidden bg-gradient-to-br from-blue-50/50 to-purple-50/50 dark:from-blue-950/20 dark:to-purple-950/20 shadow-sm hover:shadow-md transition-all duration-200">
                  {/* Gradient border effect */}
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-cyan-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                  
                  <button
                    onClick={() => toggleTool(idx)}
                    className="relative w-full flex items-center gap-2 px-3 py-2 hover:bg-white/50 dark:hover:bg-gray-800/50 transition-colors text-left"
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <div className="w-5 h-5 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/50 dark:to-purple-900/50 flex items-center justify-center flex-shrink-0 ring-1 ring-blue-200 dark:ring-blue-800">
                        <Wrench className="h-2.5 w-2.5 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-tool-name text-gray-900 dark:text-gray-100 truncate">{item.name || 'Tool'}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-600 dark:text-green-500" />
                      {isExpanded ? (
                        <ChevronUp className="h-3.5 w-3.5 text-gray-400" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
                      )}
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50/80 dark:bg-gray-800/30 p-3">
                      <div className="text-message-small font-medium text-gray-700 dark:text-gray-300 mb-2">Input:</div>
                      <pre className="text-message-small text-gray-600 dark:text-gray-400 whitespace-pre-wrap overflow-x-auto font-mono bg-white dark:bg-gray-900 p-2 rounded border border-gray-200 dark:border-gray-700 max-h-60 overflow-y-auto">
                        {JSON.stringify(item.input || item, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            );
          }
          return null;
        })}
      </div>
    );
  }

  // Fallback: render using extracted fields (only if no content array)
  return (
    <>
      {message.thinkingContent && (
        <Reasoning defaultOpen={isCurrent} isStreaming={isCurrent && !!message.thinkingContent}>
          <ReasoningTrigger />
          <ReasoningContent>{message.thinkingContent}</ReasoningContent>
        </Reasoning>
      )}

      {message.content && message.content !== '(no content)' && (
        <div className="prose dark:prose-invert prose-p:leading-relaxed prose-pre:p-0 w-full max-w-none break-words whitespace-pre-wrap">
          <ReactMarkdown 
            components={{
                a: LinkComponent,
                code({ node, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '')
                    const isInline = !match
                    return !isInline ? (
                    <CodeBlock
                        language={match![1]}
                        code={String(children).replace(/\n$/, '')}
                        className="my-4"
                    />
                    ) : (
                    <code className="bg-muted px-1.5 py-0.5 rounded font-mono text-sm" {...props}>
                        {children}
                    </code>
                    )
                }
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>
      )}

      {/* Render tool calls in fallback mode - V0 style with gradients */}
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="flex flex-col gap-2 mt-2">
          {message.toolCalls.map((tool: any, toolIdx: number) => {
            const isExpanded = expandedTools.has(1000 + toolIdx);
            return (
              <div key={tool.id} className="group">
                <div className="relative border border-blue-500/50 dark:border-blue-400/50 rounded-lg overflow-hidden bg-gradient-to-br from-blue-50/50 to-purple-50/50 dark:from-blue-950/20 dark:to-purple-950/20 shadow-sm hover:shadow-md transition-all duration-200">
                  <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-cyan-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />
                  
                  <button
                    onClick={() => toggleTool(1000 + toolIdx)}
                    className="relative w-full flex items-center gap-2 px-3 py-2 hover:bg-white/50 dark:hover:bg-gray-800/50 transition-colors text-left"
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <div className="w-5 h-5 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/50 dark:to-purple-900/50 flex items-center justify-center flex-shrink-0 ring-1 ring-blue-200 dark:ring-blue-800">
                        <Wrench className="h-2.5 w-2.5 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-tool-name text-gray-900 dark:text-gray-100 truncate">{tool.name || tool.function?.name || 'Tool'}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-600 dark:text-green-500" />
                      {isExpanded ? (
                        <ChevronUp className="h-3.5 w-3.5 text-gray-400" />
                      ) : (
                        <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
                      )}
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="border-t border-gray-200 dark:border-gray-700 bg-gray-50/80 dark:bg-gray-800/30 p-3">
                      <div className="text-message-small font-medium text-gray-700 dark:text-gray-300 mb-2">Input:</div>
                      <pre className="text-message-small text-gray-600 dark:text-gray-400 whitespace-pre-wrap overflow-x-auto font-mono bg-white dark:bg-gray-900 p-2 rounded border border-gray-200 dark:border-gray-700 max-h-60 overflow-y-auto">
                        {JSON.stringify(tool.input || tool, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  )
}
