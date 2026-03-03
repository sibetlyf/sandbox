#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时浏览器服务 - 使用 Playwright 控制真实浏览器
通过 WebSocket 实时传输浏览器画面到前端，并接收用户交互事件
"""

import asyncio
import base64
import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Real Browser Service")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BrowserInstance:
    """单个浏览器实例"""
    
    def __init__(self, browser_id: str):
        self.browser_id = browser_id
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.websockets: Set[WebSocket] = set()
        self.is_running = False
        self.screenshot_task = None
        self.current_url = "about:blank"
        self.viewport_width = 1280
        self.viewport_height = 720
        
    async def start(self):
        """启动浏览器"""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            
            # 启动 Chromium 浏览器（无头模式关闭，但我们通过截图传输）
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # 无头模式，因为我们通过截图传输
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu'
                ]
            )
            
            # 创建浏览器上下文
            self.context = await self.browser.new_context(
                viewport={'width': self.viewport_width, 'height': self.viewport_height},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 创建页面
            self.page = await self.context.new_page()
            
            # 导航到空白页
            await self.page.goto('about:blank')
            
            self.is_running = True
            logger.info(f"浏览器实例 {self.browser_id} 启动成功")
            
            return True
            
        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            return False
    
    async def stop(self):
        """停止浏览器"""
        self.is_running = False
        
        if self.screenshot_task:
            self.screenshot_task.cancel()
            
        if self.page:
            try:
                await self.page.close()
            except:
                pass
                
        if self.context:
            try:
                await self.context.close()
            except:
                pass
                
        if self.browser:
            try:
                await self.browser.close()
            except:
                pass
                
        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass
                
        logger.info(f"浏览器实例 {self.browser_id} 已停止")
    
    async def navigate(self, url: str):
        """导航到指定URL"""
        if not self.page:
            return False
            
        try:
            # 确保URL格式正确
            if not url.startswith(('http://', 'https://', 'about:')):
                url = 'http://' + url
                
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            self.current_url = url
            
            # 广播URL变化
            await self.broadcast({
                'type': 'navigation',
                'url': self.page.url,
                'title': await self.page.title()
            })
            
            return True
        except Exception as e:
            logger.error(f"导航失败: {e}")
            await self.broadcast({
                'type': 'error',
                'message': f'导航失败: {str(e)}'
            })
            return False
    
    async def click(self, x: int, y: int):
        """在指定位置点击"""
        if not self.page:
            return
            
        try:
            await self.page.mouse.click(x, y)
        except Exception as e:
            logger.error(f"点击失败: {e}")
    
    async def type_text(self, text: str):
        """输入文本"""
        if not self.page:
            return
            
        try:
            await self.page.keyboard.type(text)
        except Exception as e:
            logger.error(f"输入失败: {e}")
    
    async def press_key(self, key: str):
        """按下键盘按键"""
        if not self.page:
            return
            
        try:
            await self.page.keyboard.press(key)
        except Exception as e:
            logger.error(f"按键失败: {e}")
    
    async def scroll(self, delta_x: int, delta_y: int):
        """滚动页面"""
        if not self.page:
            return
            
        try:
            await self.page.mouse.wheel(delta_x, delta_y)
        except Exception as e:
            logger.error(f"滚动失败: {e}")
    
    async def go_back(self):
        """后退"""
        if not self.page:
            return
        try:
            await self.page.go_back()
            await self.broadcast({
                'type': 'navigation',
                'url': self.page.url,
                'title': await self.page.title()
            })
        except Exception as e:
            logger.error(f"后退失败: {e}")
    
    async def go_forward(self):
        """前进"""
        if not self.page:
            return
        try:
            await self.page.go_forward()
            await self.broadcast({
                'type': 'navigation',
                'url': self.page.url,
                'title': await self.page.title()
            })
        except Exception as e:
            logger.error(f"前进失败: {e}")
    
    async def refresh(self):
        """刷新页面"""
        if not self.page:
            return
        try:
            await self.page.reload()
            await self.broadcast({
                'type': 'navigation',
                'url': self.page.url,
                'title': await self.page.title()
            })
        except Exception as e:
            logger.error(f"刷新失败: {e}")
    
    async def take_screenshot(self) -> Optional[str]:
        """截取屏幕并返回 base64 编码的图片"""
        if not self.page:
            return None
            
        try:
            screenshot = await self.page.screenshot(
                type='jpeg',
                quality=75,  # 降低质量以提高传输速度
                full_page=False
            )
            return base64.b64encode(screenshot).decode('utf-8')
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    async def start_screenshot_stream(self, fps: int = 10):
        """开始截图流"""
        interval = 1.0 / fps
        
        while self.is_running and len(self.websockets) > 0:
            try:
                screenshot = await self.take_screenshot()
                if screenshot:
                    await self.broadcast({
                        'type': 'screenshot',
                        'data': screenshot,
                        'url': self.page.url if self.page else '',
                        'title': await self.page.title() if self.page else '',
                        'timestamp': datetime.now().isoformat()
                    })
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"截图流错误: {e}")
                await asyncio.sleep(0.5)
    
    async def broadcast(self, message: dict):
        """广播消息给所有连接的 WebSocket"""
        disconnected = set()
        
        for ws in self.websockets:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        
        # 清理断开的连接
        self.websockets -= disconnected
    
    def add_websocket(self, ws: WebSocket):
        """添加 WebSocket 连接"""
        self.websockets.add(ws)
        
        # 如果这是第一个连接，启动截图流
        if len(self.websockets) == 1 and not self.screenshot_task:
            self.screenshot_task = asyncio.create_task(self.start_screenshot_stream())
    
    def remove_websocket(self, ws: WebSocket):
        """移除 WebSocket 连接"""
        self.websockets.discard(ws)
        
        # 如果没有连接了，停止截图流
        if len(self.websockets) == 0 and self.screenshot_task:
            self.screenshot_task.cancel()
            self.screenshot_task = None


class BrowserManager:
    """浏览器管理器"""
    
    def __init__(self):
        self.browsers: Dict[str, BrowserInstance] = {}
        self.default_browser: Optional[BrowserInstance] = None
        self.lock = asyncio.Lock()
    
    async def get_or_create_browser(self, browser_id: str = "default") -> Optional[BrowserInstance]:
        """获取或创建浏览器实例"""
        async with self.lock:
            if browser_id in self.browsers:
                return self.browsers[browser_id]
            
            # 创建新的浏览器实例
            browser = BrowserInstance(browser_id)
            if await browser.start():
                self.browsers[browser_id] = browser
                if browser_id == "default":
                    self.default_browser = browser
                return browser
            
            return None
    
    async def close_browser(self, browser_id: str):
        """关闭浏览器实例"""
        async with self.lock:
            if browser_id in self.browsers:
                browser = self.browsers[browser_id]
                await browser.stop()
                del self.browsers[browser_id]
                if self.default_browser == browser:
                    self.default_browser = None
    
    async def close_all(self):
        """关闭所有浏览器"""
        async with self.lock:
            for browser in list(self.browsers.values()):
                await browser.stop()
            self.browsers.clear()
            self.default_browser = None


# 全局浏览器管理器
browser_manager = BrowserManager()


@app.websocket("/ws/browser")
async def browser_websocket(websocket: WebSocket):
    """浏览器 WebSocket 端点"""
    await websocket.accept()
    
    browser_id = "default"
    browser = await browser_manager.get_or_create_browser(browser_id)
    
    if not browser:
        await websocket.send_json({
            'type': 'error',
            'message': '无法启动浏览器，请确保已安装 Playwright 和浏览器'
        })
        await websocket.close()
        return
    
    # 添加 WebSocket 连接
    browser.add_websocket(websocket)
    
    # 发送初始状态
    await websocket.send_json({
        'type': 'connected',
        'browser_id': browser_id,
        'viewport': {
            'width': browser.viewport_width,
            'height': browser.viewport_height
        },
        'url': browser.page.url if browser.page else 'about:blank'
    })
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            action = data.get('action')
            
            if action == 'navigate':
                url = data.get('url', '')
                await browser.navigate(url)
                
            elif action == 'click':
                x = data.get('x', 0)
                y = data.get('y', 0)
                await browser.click(x, y)
                
            elif action == 'type':
                text = data.get('text', '')
                await browser.type_text(text)
                
            elif action == 'keypress':
                key = data.get('key', '')
                await browser.press_key(key)
                
            elif action == 'scroll':
                delta_x = data.get('deltaX', 0)
                delta_y = data.get('deltaY', 0)
                await browser.scroll(delta_x, delta_y)
                
            elif action == 'back':
                await browser.go_back()
                
            elif action == 'forward':
                await browser.go_forward()
                
            elif action == 'refresh':
                await browser.refresh()
                
            elif action == 'screenshot':
                # 手动请求一次截图
                screenshot = await browser.take_screenshot()
                if screenshot:
                    await websocket.send_json({
                        'type': 'screenshot',
                        'data': screenshot,
                        'url': browser.page.url if browser.page else '',
                        'timestamp': datetime.now().isoformat()
                    })
                    
    except WebSocketDisconnect:
        logger.info(f"浏览器 WebSocket 断开连接: {browser_id}")
    except Exception as e:
        logger.error(f"浏览器 WebSocket 错误: {e}")
    finally:
        browser.remove_websocket(websocket)
        
        # 如果没有连接了，5秒后关闭浏览器
        if len(browser.websockets) == 0:
            await asyncio.sleep(5)
            if len(browser.websockets) == 0:
                await browser_manager.close_browser(browser_id)


@app.get("/api/browser/status")
async def browser_status():
    """获取浏览器状态"""
    return {
        "active_browsers": len(browser_manager.browsers),
        "browsers": [
            {
                "id": bid,
                "url": b.page.url if b.page else None,
                "connections": len(b.websockets),
                "is_running": b.is_running
            }
            for bid, b in browser_manager.browsers.items()
        ]
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "service": "browser"}


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": "Real Browser Service",
        "version": "1.0.0",
        "websocket_endpoint": "/ws/browser",
        "description": "实时浏览器控制服务，通过WebSocket传输浏览器画面"
    }


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    await browser_manager.close_all()


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("BROWSER_PORT", 5690))
    host = os.environ.get("BROWSER_HOST", "0.0.0.0")
    print(f"启动实时浏览器服务: {host}:{port}")
    uvicorn.run(app, host=host, port=port)
