
'use client'

import { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Cloud, ExternalLink, Loader2, CheckCircle2, Square } from 'lucide-react'
import { useWebSocketContext } from '@/hooks/websocket-context'

export function DeployDialog() {
  const { sendMessage, lastMessage, cancelTask, setPreviewUrl } = useWebSocketContext()
  const [open, setOpen] = useState(false)
  
  // EdgeOne State
  const [token, setToken] = useState('')
  const [projectName, setProjectName] = useState('')
  
  // Local Deploy State
  const [activeTab, setActiveTab] = useState<'local' | 'edgeone'>('local')
  const [projects, setProjects] = useState<string[]>([])
  const [selectedProject, setSelectedProject] = useState<string>('')
  const [isDeploying, setIsDeploying] = useState(false)
  const [deployLogs, setDeployLogs] = useState<string>('')
  const [deployUrl, setDeployUrl] = useState<string>('')
  
  const currentTaskId = useRef<string | null>(null)

  // 监听 WebSocket 消息
  useEffect(() => {
    if (!lastMessage) return

    try {
      const data = JSON.parse(lastMessage.data)
      
      // 检查消息是否属于当前任务 (如果有关联的话)
      // 注意: 这里 backend 广播的消息包含 task_id, 但我们可能收到其他任务的消息
      // 简单起见，假设 log window 显示所有相关消息，或者我们可以过滤
      if (currentTaskId.current && data.task_id && data.task_id !== currentTaskId.current) {
          return
      }

      // 处理部署日志
      if (data.type === 'chunk' && data.new_text) {
        setDeployLogs(prev => prev + data.new_text)
      }
      
      // 处理部署成功
      if (data.type === 'deploy_success' && data.url) {
        setDeployUrl(data.url)
        // 保持 isDeploying 为 true，因为服务器仍在运行
        
        // 1. 设置预览 URL 为 VNC 地址 (让用户看到沙箱浏览器)
        const vncUrl = process.env.NEXT_PUBLIC_BROWSER_URL || 'http://localhost:9020/vnc/index.html?autoconnect=true'
        if (setPreviewUrl) {
            setPreviewUrl(vncUrl)
        } else {
             console.warn("setPreviewUrl not found in context")
        }

        // 2. 自动控制沙箱浏览器跳转到部署地址 (通过 Browser Service)
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsHost = window.location.host
        const browserWs = new WebSocket(`${wsProtocol}//${wsHost}/ws/browser`)
        
        browserWs.onopen = () => {
          console.log('Connected to Browser Service, navigating to:', data.url)
          browserWs.send(JSON.stringify({
            action: 'navigate',
            url: data.url
          }))
          // 同时也请求截图
          setTimeout(() => {
             browserWs.send(JSON.stringify({ action: 'screenshot' }))
          }, 2000)
        }
      }
      
      // 处理错误
      if (data.type === 'error') {
        setDeployLogs(prev => prev + `\n❌ Error: ${data.message}\n`)
        setIsDeploying(false)
        currentTaskId.current = null
      }

      // 处理任务取消/完成
      if (data.type === 'task_cancelled' || data.type === 'task_complete') {
          setIsDeploying(false)
          setDeployLogs(prev => prev + `\n✨ Task ${data.type === 'task_cancelled' ? 'Stopped' : 'Completed'}.\n`)
          currentTaskId.current = null
      }
      
    } catch (e) {
      console.error('Failed to parse websocket message', e)
    }
  }, [lastMessage])

  // 扫描项目
  const scanProjects = async () => {
    try {
      const response = await fetch('/api/sandbox/api/workspace/files')
      if (response.ok) {
        const data = await response.json()
        // 简单逻辑：查找包含 package.json 的目录
        const projectDirs: string[] = []
        
        //Helper to check dir recursively (limit depth)
        const checkDir = (items: any[], path: string) => {
             const hasPackageJson = items.some(f => f.name === 'package.json')
             if (hasPackageJson) {
                 projectDirs.push(path || 'root')
             }
             
             // Continue searching in subdirectories
             items.filter(i => i.type === 'directory').forEach(dir => {
                 checkDir(dir.children || [], dir.path)
             })
        }
        
        checkDir(data.files || [], '')
        setProjects(projectDirs)
        if (projectDirs.length > 0 && !selectedProject) {
            setSelectedProject(projectDirs[0])
        }
    }
    } catch (e) {
      console.error('Failed to scan projects', e)
    }
  }

  // 打开对话框时扫描项目
  useEffect(() => {
    if (open && activeTab === 'local') {
        scanProjects()
    }
  }, [open, activeTab])

  const handleEdgeOneDeploy = () => {
    if (!token || !projectName) return

    const deployRequest = JSON.stringify({
      action: 'deploy_edgeone',
      project_name: projectName,
      token: token,
      environment: 'preview'
    })
    
    sendMessage(deployRequest)
    setOpen(false)
  }

  const handleLocalDeploy = () => {
      if (!selectedProject) return
      
      setIsDeploying(true)
      setDeployLogs('🚀 Starting local deployment...\n')
      setDeployUrl('')
      
      const taskId = `deploy_${Date.now()}`
      currentTaskId.current = taskId
      
      const deployRequest = JSON.stringify({
          action: 'deploy_local',
          project_path: selectedProject === 'root' ? '' : selectedProject
      })
      
      sendMessage(deployRequest, { task_id: taskId })
  }

  const handleStopDeploy = () => {
      if (currentTaskId.current) {
          cancelTask(currentTaskId.current)
          setDeployLogs(prev => prev + '\n🛑 Stopping deployment...\n')
      }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button className="group px-4 py-2.5 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 rounded-xl transition-all duration-200 flex items-center gap-2 shadow-md hover:shadow-lg hover:scale-105 active:scale-95">
          <Cloud className="h-4 w-4 transition-transform group-hover:scale-110" />
          <span className="hidden sm:inline">一键部署</span>
        </button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Project Deployment</DialogTitle>
          <DialogDescription>
            Deploy your project locally or to EdgeOne Pages.
          </DialogDescription>
        </DialogHeader>

        <div className="flex border-b mb-4">
            <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'local' 
                    ? 'border-blue-500 text-blue-600' 
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
                onClick={() => setActiveTab('local')}
            >
                Local Deploy
            </button>
            <button
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'edgeone' 
                    ? 'border-purple-500 text-purple-600' 
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                }`}
                onClick={() => setActiveTab('edgeone')}
            >
                EdgeOne Pages
            </button>
        </div>

        {activeTab === 'local' ? (
            <div className="space-y-4 flex-1 overflow-hidden flex flex-col">
                <div className="grid gap-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <label className="text-right text-sm font-medium">Project</label>
                        <select 
                            className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            value={selectedProject}
                            onChange={(e) => setSelectedProject(e.target.value)}
                        >
                            {projects.length === 0 && <option value="">No projects found</option>}
                            {projects.map(p => (
                                <option key={p} value={p}>{p === 'root' ? '/ (Root)' : p}</option>
                            ))}
                        </select>
                    </div>
                </div>

                <div className="flex-1 min-h-[200px] bg-black/90 rounded-md p-3 overflow-auto font-mono text-xs text-green-400">
                    <pre className="whitespace-pre-wrap break-all">
                        {deployLogs || 'Ready to deploy...'}
                    </pre>
                </div>
                
                {deployUrl && (
                    <div className="p-2 bg-green-500/10 border border-green-500/20 rounded text-green-600 text-sm flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4" />
                        Deployed successfully: 
                        <a href={deployUrl} target="_blank" rel="noopener noreferrer" className="underline font-bold">
                            {deployUrl}
                        </a>
                    </div>
                )}

                <DialogFooter className="gap-2">
                    {isDeploying && (
                        <Button 
                            variant="destructive"
                            onClick={handleStopDeploy}
                            className="flex items-center gap-2"
                        >
                            <Square className="h-4 w-4 fill-current" />
                            Stop Service
                        </Button>
                    )}
                    
                    <Button 
                        onClick={handleLocalDeploy} 
                        disabled={!selectedProject || isDeploying}
                        className={isDeploying ? "opacity-50 cursor-not-allowed" : ""}
                    >
                        {isDeploying ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Deploying...
                            </>
                        ) : 'Start Deploy'}
                    </Button>
                </DialogFooter>
            </div>
        ) : (
            <div className="space-y-4">
                 <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="token" className="text-right text-sm font-medium">
                      Token
                    </label>
                    <Input
                      id="token"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="EdgeOne API Token"
                      type="password"
                      className="col-span-3"
                    />
                  </div>
                  <div className="grid grid-cols-4 items-center gap-4">
                    <label htmlFor="project" className="text-right text-sm font-medium">
                      Project
                    </label>
                    <Input
                      id="project"
                      value={projectName}
                      onChange={(e) => setProjectName(e.target.value)}
                      placeholder="Project Name"
                      className="col-span-3"
                    />
                  </div>
                  <div className="flex justify-end">
                    <a 
                      href="https://console.tencentcloud.com/edgeone/pages" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-blue-500 hover:text-blue-700 flex items-center"
                    >
                      Manage Projects <ExternalLink className="ml-1 h-3 w-3" />
                    </a>
                  </div>
                </div>
                <DialogFooter>
                  <Button onClick={handleEdgeOneDeploy} disabled={!token || !projectName}>
                    Deploy to EdgeOne
                  </Button>
                </DialogFooter>
            </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
