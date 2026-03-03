'use client'

import * as React from 'react'
import { MessageSquare, Settings, Plus, Folder, FileCode, Moon, Sun } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useWebSocketContext } from '@/hooks/websocket-context'
import { SettingsDialog } from '@/components/settings-dialog'
import { DeployDialog } from '@/components/deploy-dialog'

interface AppSidebarProps extends React.HTMLAttributes<HTMLDivElement> {}

export function AppSidebar({ className, ...props }: AppSidebarProps) {
  const { startNewSession, currentSessionId, isConnected, sessions, loadSession, setFloatingPanel } = useWebSocketContext()
  
  return (
    <div className={cn("pb-12 min-h-screen border-r bg-sidebar", className)} {...props}>
      <div className="space-y-4 py-4">
        <div className="px-3 py-2">
          <div className="space-y-1">
            <Button 
                variant="secondary" 
                className="w-full justify-start mb-2" 
                onClick={startNewSession}
            >
              <Plus className="mr-2 h-4 w-4" />
              New Chat
            </Button>
            
            <Button 
                variant="outline" 
                className="w-full justify-start mb-4" 
                onClick={() => setFloatingPanel({ isOpen: true, activeTab: 'files' })}
            >
              <FileCode className="mr-2 h-4 w-4" />
              工作区文件
            </Button>
            
            <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
              History
            </h2>
            <ScrollArea className="h-[300px] px-1">
              <div className="space-y-1 p-2">
                {sessions && sessions.length > 0 ? (
                    sessions.map((chat) => (
                      <Button
                        key={chat.session_id}
                        variant={currentSessionId === chat.session_id ? "secondary" : "ghost"}
                        className="w-full justify-start font-normal truncate"
                        title={chat.session_id}
                        onClick={() => loadSession(chat.session_id)}
                      >
                        <MessageSquare className="mr-2 h-4 w-4 flex-shrink-0" />
                        <span className="truncate">
                            {chat.timestamp ? new Date(chat.timestamp).toLocaleString() : 'Unknown time'}
                        </span>
                      </Button>
                    ))
                ) : (
                    <div className="text-sm text-muted-foreground px-4 py-2">
                        No history found
                    </div>
                )}
            </div>
            </ScrollArea>
          </div>
        </div>
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
            Projects
          </h2>
          <div className="space-y-1">
             <Button variant="ghost" className="w-full justify-start">
               <Folder className="mr-2 h-4 w-4" />
               Project A
             </Button>
          </div>
        </div>
      </div>
      <div className="absolute bottom-4 left-4 right-4 space-y-2">
         <Button 
           variant="ghost" 
           className="w-full justify-start"
           onClick={() => document.documentElement.classList.toggle('dark')}
         >
           <Moon className="mr-2 h-4 w-4 dark:hidden" />
           <Sun className="mr-2 h-4 w-4 hidden dark:block" />
           <span className="dark:hidden">Dark Mode</span>
           <span className="hidden dark:block">Light Mode</span>
         </Button>
         <div className="flex items-center gap-2 px-2 text-xs">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-muted-foreground">
                {isConnected ? 'Connected' : 'Disconnected'}
            </span>
         </div>
         <SettingsDialog />
         <DeployDialog />
      </div>
    </div>
  )
}
