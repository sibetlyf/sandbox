'use client'

import { useState, useEffect } from 'react'
import { ChevronRight, ChevronDown, File, Folder, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  size?: number
}

interface FileBrowserProps {
  onFileSelect?: (filePath: string) => void
  selectedFile?: string | null
}

export function FileBrowser({ onFileSelect, selectedFile }: FileBrowserProps) {
  const [files, setFiles] = useState<FileNode[]>([])
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFiles()
  }, [])

  const fetchFiles = async () => {
    try {
      // 使用 Next.js 代理路径，而不是直接访问后端
      // 原有逻辑：直接构造 http://${host}:${port}/api/workspace/files
      // 新逻辑：使用相对路径 /api/sandbox/api/workspace/files，由 Next.js rewrites 转发
      const response = await fetch('/api/sandbox/api/workspace/files')
      if (response.ok) {
        const data = await response.json()
        setFiles(data.files || [])
      }
    } catch (error) {
      console.error('Failed to fetch files:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleDirectory = (path: string) => {
    const newExpanded = new Set(expandedDirs)
    if (newExpanded.has(path)) {
      newExpanded.delete(path)
    } else {
      newExpanded.add(path)
    }
    setExpandedDirs(newExpanded)
  }

  const renderFileTree = (nodes: FileNode[], level = 0) => {
    return nodes
      .filter(node => 
        searchQuery === '' || 
        node.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
      .map(node => (
        <div key={node.path}>
          <Button
            variant="ghost"
            className={cn(
              "w-full justify-start font-normal h-8 px-2",
              selectedFile === node.path && "bg-accent"
            )}
            style={{ paddingLeft: `${level * 12 + 8}px` }}
            onClick={() => {
              if (node.type === 'directory') {
                toggleDirectory(node.path)
              } else {
                onFileSelect?.(node.path)
              }
            }}
          >
            {node.type === 'directory' ? (
              <>
                {expandedDirs.has(node.path) ? (
                  <ChevronDown className="h-4 w-4 mr-1 flex-shrink-0" />
                ) : (
                  <ChevronRight className="h-4 w-4 mr-1 flex-shrink-0" />
                )}
                <Folder className="h-4 w-4 mr-2 flex-shrink-0 text-blue-500" />
              </>
            ) : (
              <>
                <File className="h-4 w-4 mr-2 ml-5 flex-shrink-0 text-muted-foreground" />
              </>
            )}
            <span className="truncate">{node.name}</span>
            {node.size && (
              <span className="ml-auto text-xs text-muted-foreground">
                {formatFileSize(node.size)}
              </span>
            )}
          </Button>
          {node.type === 'directory' && expandedDirs.has(node.path) && node.children && (
            <div>
              {renderFileTree(node.children, level + 1)}
            </div>
          )}
        </div>
      ))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-2 border-b">
        <div className="relative">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索文件..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
      </div>
      <ScrollArea className="flex-1">
        {loading ? (
          <div className="p-4 text-center text-muted-foreground">加载中...</div>
        ) : files.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground">工作区为空</div>
        ) : (
          <div className="p-2">
            {renderFileTree(files)}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
