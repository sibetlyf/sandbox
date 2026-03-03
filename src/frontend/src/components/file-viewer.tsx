'use client'

import { useState, useEffect } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2 } from 'lucide-react'

interface FileViewerProps {
  filePath: string | null
}

export function FileViewer({ filePath }: FileViewerProps) {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (filePath) {
      fetchFileContent(filePath)
    }
  }, [filePath])

  const fetchFileContent = async (path: string) => {
    setLoading(true)
    setError(null)
    try {
      // 使用 Next.js 代理路径，而不是直接访问后端
      // 原有逻辑：直接构造 http://${host}:${port}/api/workspace/file-content
      // 新逻辑：使用相对路径 /api/sandbox/api/workspace/file-content，由 Next.js rewrites 转发
      const response = await fetch(`/api/sandbox/api/workspace/file-content?file_path=${encodeURIComponent(path)}`)
      if (response.ok) {
        const data = await response.json()
        setContent(data.content || '')
      } else {
        setError('无法读取文件')
      }
    } catch (err) {
      setError('读取文件时出错')
      console.error('Failed to fetch file content:', err)
    } finally {
      setLoading(false)
    }
  }

  const getLanguage = (path: string) => {
    const ext = path.split('.').pop()?.toLowerCase()
    const languageMap: Record<string, string> = {
      'js': 'javascript',
      'jsx': 'jsx',
      'ts': 'typescript',
      'tsx': 'tsx',
      'py': 'python',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'go': 'go',
      'rs': 'rust',
      'php': 'php',
      'rb': 'ruby',
      'swift': 'swift',
      'kt': 'kotlin',
      'json': 'json',
      'xml': 'xml',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'md': 'markdown',
      'yaml': 'yaml',
      'yml': 'yaml',
      'sh': 'bash',
      'sql': 'sql'
    }
    return languageMap[ext || ''] || 'text'
  }

  if (!filePath) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        选择要查看的文件
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-destructive">
        {error}
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-4">
        <div className="mb-2 text-sm text-muted-foreground font-mono">
          {filePath}
        </div>
        <SyntaxHighlighter
          language={getLanguage(filePath)}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            borderRadius: '0.5rem',
            fontSize: '0.875rem'
          }}
          showLineNumbers
        >
          {content}
        </SyntaxHighlighter>
      </div>
    </ScrollArea>
  )
}
