'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
// Use standard label if available or create simple one
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Settings } from 'lucide-react'

export function SettingsDialog() {
  const [open, setOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const [host, setHost] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('vibe_ws_host') || process.env.NEXT_PUBLIC_WS_HOST || 'localhost'
    }
    return 'localhost'
  })
  const [port, setPort] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('vibe_ws_port') || process.env.NEXT_PUBLIC_WS_PORT || '9999'
    }
    return '9999'
  })
  const [password, setPassword] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('vibe_ws_password') || process.env.NEXT_PUBLIC_WS_PASSWORD || ''
    }
    return ''
  })

  useEffect(() => {
    if (open) {
      // Use setTimeout to avoid synchronous state update warning during render
      const timer = setTimeout(() => {
        const savedHost = localStorage.getItem('vibe_ws_host') || process.env.NEXT_PUBLIC_WS_HOST || 'localhost'
        const savedPort = localStorage.getItem('vibe_ws_port') || process.env.NEXT_PUBLIC_WS_PORT || '9999'
        const savedPassword = localStorage.getItem('vibe_ws_password') || process.env.NEXT_PUBLIC_WS_PASSWORD || ''
        setHost(savedHost)
        setPort(savedPort)
        setPassword(savedPassword)
      }, 0)
      return () => clearTimeout(timer)
    }
  }, [open])

  const handleSave = () => {
    setIsLoading(true)
    localStorage.setItem('vibe_ws_host', host)
    localStorage.setItem('vibe_ws_port', port)
    localStorage.setItem('vibe_ws_password', password)
    
    // Simulate save delay
    setTimeout(() => {
        setIsLoading(false)
        setOpen(false)
        // Force reload to apply new connection settings (simplest way for now)
        window.location.reload() 
    }, 500)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" className="w-full justify-start">
            <Settings className="mr-2 h-4 w-4" />
            Settings
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Configure the connection to the AI Backend.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <label htmlFor="host" className="text-right text-sm font-medium">
              Host
            </label>
            <Input
              id="host"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              className="col-span-3"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <label htmlFor="port" className="text-right text-sm font-medium">
              Port
            </label>
            <Input
              id="port"
              value={port}
              onChange={(e) => setPort(e.target.value)}
              className="col-span-3"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <label htmlFor="password" className="text-right text-sm font-medium">
              Password
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Optional"
              className="col-span-3"
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading ? 'Saving...' : 'Save changes'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
