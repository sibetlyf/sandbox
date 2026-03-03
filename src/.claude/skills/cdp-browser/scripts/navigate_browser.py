#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CDP Browser Navigation Script

This script connects to a Chrome browser via CDP and navigates to a specified URL.
It can extract page title, URL, and content.

Usage:
    python navigate_browser.py --url "https://example.com"
    python navigate_browser.py --url "http://localhost:3000" --port 8080 --wait 5
"""

import pychrome
import time
import argparse
import sys


def navigate_to_url(url, cdp_port=8080, wait_time=5, extract_all=False):
    """
    Navigate browser to specified URL and extract page information.
    
    Args:
        url (str): Target URL to navigate to
        cdp_port (int): CDP port number (default: 8080)
        wait_time (int): Time to wait for page load in seconds (default: 5)
        extract_all (bool): Extract full page text instead of preview
        
    Returns:
        dict: Page information including title, url, and content
    """
    # 连接到浏览器
    print(f"连接到 CDP 浏览器 (端口 {cdp_port})...")
    browser = pychrome.Browser(url=f"http://localhost:{cdp_port}")
    tab = browser.new_tab()
    
    result_data = {}
    
    try:
        # 启动标签页
        tab.start()
        
        # 启用必要的域
        tab.Page.enable()
        tab.Runtime.enable()
        
        # 导航到指定 URL
        print(f"正在导航到：{url}")
        nav_result = tab.Page.navigate(url=url)
        print(f"导航结果：{nav_result}")
        result_data['navigation'] = nav_result
        
        # 等待页面加载
        print(f"等待页面加载 ({wait_time} 秒)...")
        time.sleep(wait_time)
        
        # 获取页面信息
        print("\n=== 页面信息 ===")
        
        # 获取标题
        try:
            title = tab.Runtime.evaluate(expression="document.title")
            title_value = title.get('result', {}).get('value', 'N/A')
            print(f"标题：{title_value}")
            result_data['title'] = title_value
        except Exception as e:
            print(f"获取标题失败：{e}")
            result_data['title'] = None
        
        # 获取 URL
        try:
            url_result = tab.Runtime.evaluate(expression="window.location.href")
            url_value = url_result.get('result', {}).get('value', 'N/A')
            print(f"URL：{url_value}")
            result_data['url'] = url_value
        except Exception as e:
            print(f"获取 URL 失败：{e}")
            result_data['url'] = None
        
        # 获取页面内容
        try:
            if extract_all:
                content_expr = "document.body.innerText"
            else:
                content_expr = "document.body.innerText.substring(0, 300)"
            
            content = tab.Runtime.evaluate(expression=content_expr)
            content_value = content.get('result', {}).get('value', 'N/A')
            print(f"\n页面内容预览：\n{content_value}")
            result_data['content'] = content_value
        except Exception as e:
            print(f"获取内容失败：{e}")
            result_data['content'] = None
        
        return result_data
        
    except Exception as e:
        print(f"\n错误：{e}")
        result_data['error'] = str(e)
        return result_data
        
    finally:
        # 保持标签页打开，不进行清理
        print("\n✓ 导航完成，标签页保持打开状态")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Navigate Chrome browser via CDP to specified URL',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url "https://www.baidu.com"
  %(prog)s --url "http://localhost:3000" --port 8080 --wait 3
  %(prog)s -u "https://example.com" -p 9222 -w 5 --extract-all
        """
    )
    
    parser.add_argument(
        '--url', '-u',
        required=True,
        help='Target URL to navigate to (e.g., https://example.com)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8080,
        help='CDP port number (default: 8080)'
    )
    
    parser.add_argument(
        '--wait', '-w',
        type=int,
        default=5,
        help='Wait time for page load in seconds (default: 5)'
    )
    
    parser.add_argument(
        '--extract-all',
        action='store_true',
        help='Extract full page text instead of preview (first 300 chars)'
    )
    
    args = parser.parse_args()
    
    # Execute navigation
    result = navigate_to_url(
        url=args.url,
        cdp_port=args.port,
        wait_time=args.wait,
        extract_all=args.extract_all
    )
    
    # Exit with appropriate code
    if 'error' in result:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
