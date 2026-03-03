from playwright.sync_api import sync_playwright
import time
import os

# 前端地址 (根据你的 run.sh 输出调整，通常 Next.js 是 3000)
FRONTEND_URL = "http://localhost:3000"

def run_frontend_test():
    with sync_playwright() as p:
        print("🚀 启动浏览器模拟用户交互...")
        # headless=False 让你可以看到浏览器操作过程
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            print(f"🌐 正在访问: {FRONTEND_URL}")
            page.goto(FRONTEND_URL)
            
            # 等待页面核心元素加载
            page.wait_for_load_state("networkidle")
            print("✅ 页面已加载")

            # 模拟用户交互：寻找输入框
            # 尝试常见的聊天输入框选择器 (textarea 或 input)
            input_selector = "textarea"
            if not page.query_selector(input_selector):
                input_selector = "input[type='text']"
            
            if page.query_selector(input_selector):
                print(f"⌨️  找到输入框 ({input_selector})，正在输入测试消息...")
                page.click(input_selector)
                page.fill(input_selector, "你好，这是一个自动化的前端测试消息。")
                time.sleep(1)

                print("🖱️  模拟按下回车键发送...")
                page.keyboard.press("Enter")
                
                # 或者尝试点击发送按钮 (通常包含 svg 图标或 send 文本)
                # send_btn = page.query_selector("button[type='submit']")
                # if send_btn:
                #     send_btn.click()
                
                print("⏳ 等待 3 秒观察响应...")
                time.sleep(3)
            else:
                print("⚠️  未找到输入框，仅截图页面状态。")

            # 截图保存结果
            screenshot_path = "frontend_test_result.png"
            page.screenshot(path=screenshot_path)
            print(f"📸 测试截图已保存: {os.path.abspath(screenshot_path)}")

        except Exception as e:
            print(f"❌ 测试过程中出错: {e}")
            # 出错也截图
            page.screenshot(path="frontend_error.png")
        
        finally:
            browser.close()
            print("🏁 测试结束")

if __name__ == "__main__":
    run_frontend_test()
