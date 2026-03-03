'use client'

import React, { createContext, useContext, ReactNode } from 'react'
import { useWebSocket, WebSocketState } from './use-websocket'

const WebSocketContext = createContext<WebSocketState | null>(null)

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const websocketState = useWebSocket()
  
  return (
    <WebSocketContext.Provider value={websocketState}>
      {children}
    </WebSocketContext.Provider>
  )
}

export function useWebSocketContext() {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocketContext must be used within WebSocketProvider')
  }
  return context
}
