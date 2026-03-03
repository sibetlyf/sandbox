'use client'

import { useState } from 'react'
import { RefreshCw, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

// 从环境变量读取默认浏览器 URL
const DEFAULT_BROWSER_URL = process.env.NEXT_PUBLIC_BROWSER_URL || '';

interface IframePreviewProps {
  initialUrl?: string
}

export function IframePreview({ initialUrl = DEFAULT_BROWSER_URL }: IframePreviewProps) {
  const [url, setUrl] = useState(initialUrl)
  const [currentUrl, setCurrentUrl] = useState(initialUrl)
  const [key, setKey] = useState(0)

  const handleLoad = () => {
    setCurrentUrl(url)
  }

  const handleRefresh = () => {
    setKey(prev => prev + 1)
  }

  const handleOpenExternal = () => {
    if (currentUrl) {
      window.open(currentUrl, '_blank')
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Address bar */}
      <div className="flex items-center gap-2 p-2 border-b bg-muted/30">
        <Input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleLoad()
            }
          }}
          placeholder="输入 URL..."
          className="flex-1"
        />
        <Button
          variant="outline"
          size="icon"
          onClick={handleRefresh}
          title="刷新"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={handleOpenExternal}
          title="在新标签页打开"
        >
          <ExternalLink className="h-4 w-4" />
        </Button>
      </div>

      {/* Iframe */}
      <div className="flex-1 relative bg-white">
        {currentUrl ? (
          <iframe
            key={key}
            src={currentUrl}
            className="w-full h-full border-0"
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-downloads"
            title="Preview"
          />
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            输入 URL 以预览网页
          </div>
        )}
      </div>
    </div>
  )
}
