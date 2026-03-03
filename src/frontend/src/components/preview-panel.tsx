'use client'

import { ExternalLink, X, RefreshCw, ChevronRight, ChevronLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface PreviewPanelProps {
  url: string | null
  onClose: () => void
  className?: string
}

export function PreviewPanel({ url, onClose, className }: PreviewPanelProps) {
  const [currentUrl, setCurrentUrl] = useState(url || '')
  const [inputUrl, setInputUrl] = useState(url || '')
  const [key, setKey] = useState(0)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (url) {
      setCurrentUrl(url)
      setInputUrl(url)
      setKey(k => k + 1)
      setIsLoading(true)
    }
  }, [url])

  if (!url && !currentUrl) return null

  const handleRefresh = () => {
    setKey(prev => prev + 1)
    setIsLoading(true)
  }

  const handleLoadUrl = () => {
    if (inputUrl.trim()) {
      setCurrentUrl(inputUrl.trim())
      setKey(prev => prev + 1)
      setIsLoading(true)
    }
  }

  return (
    <div className={cn("flex flex-col h-full border-l bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60", className)}>
      {/* Browser Toolbar */}
      <div className="flex items-center gap-2 p-2 border-b h-14 bg-muted/30">
        <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground" disabled>
                <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground" disabled>
                <ChevronRight className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleRefresh}>
                <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
            </Button>
        </div>

        <div className="flex-1 relative">
            <div className="absolute inset-y-0 left-2 flex items-center pointer-events-none opacity-50">
                <span className="text-xs">🔒</span>
            </div>
            <Input 
                value={inputUrl} 
                onChange={(e) => setInputUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    handleLoadUrl()
                  }
                }}
                placeholder="输入 URL 并按 Enter..."
                className="h-8 pl-8 text-xs font-mono bg-background border-muted shadow-none focus-visible:ring-1" 
            />
        </div>

        <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
                <a href={currentUrl} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="h-4 w-4" />
                </a>
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive" onClick={onClose}>
                <X className="h-4 w-4" />
            </Button>
        </div>
      </div>

      {/* Iframe Content */}
      <div className="flex-1 relative bg-white">
        <iframe
            key={key}
            src={currentUrl}
            className="absolute inset-0 w-full h-full border-0"
            title="Preview"
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
            onLoad={() => setIsLoading(false)}
        />
        {isLoading && (
             <div className="absolute inset-0 flex items-center justify-center bg-background/50 backdrop-blur-sm z-10">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
             </div>
        )}
      </div>
    </div>
  )
}
