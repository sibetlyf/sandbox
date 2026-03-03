'use client'

import ChatInterface from '@/components/chat-interface'
import { WebSocketProvider } from '@/hooks/websocket-context'

export default function Home() {
  return (
    <div className="h-screen w-full">
      <WebSocketProvider>
        <ChatInterface />
      </WebSocketProvider>
    </div>
  )
}
