#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Advanced CDP Browser Usage Examples

This file demonstrates advanced usage patterns for CDP browser control.
"""

import pychrome
import time
import base64


def example_screenshot(url, cdp_port=8080, output_file="screenshot.png"):
    """
    Navigate to URL and take a screenshot.
    
    Args:
        url (str): Target URL
        cdp_port (int): CDP port
        output_file (str): Output screenshot filename
    """
    browser = pychrome.Browser(url=f"http://localhost:{cdp_port}")
    tab = browser.new_tab()
    
    try:
        tab.start()
        tab.Page.enable()
        
        # Navigate
        tab.Page.navigate(url=url)
        time.sleep(3)
        
        # Capture screenshot
        screenshot = tab.Page.captureScreenshot(format='png')
        
        # Save to file
        with open(output_file, 'wb') as f:
            f.write(base64.b64decode(screenshot['data']))
        
        print(f"Screenshot saved to {output_file}")
        
    finally:
        tab.stop()
        browser.close_tab(tab)


def example_wait_for_element(url, selector, cdp_port=8080, timeout=10):
    """
    Navigate to URL and wait for a specific element to appear.
    
    Args:
        url (str): Target URL
        selector (str): CSS selector to wait for
        cdp_port (int): CDP port
        timeout (int): Maximum wait time in seconds
    
    Returns:
        bool: True if element found, False if timeout
    """
    browser = pychrome.Browser(url=f"http://localhost:{cdp_port}")
    tab = browser.new_tab()
    
    try:
        tab.start()
        tab.Page.enable()
        tab.Runtime.enable()
        
        # Navigate
        tab.Page.navigate(url=url)
        
        # Wait for element
        start = time.time()
        while time.time() - start < timeout:
            result = tab.Runtime.evaluate(
                expression=f"document.querySelector('{selector}') !== null"
            )
            if result.get('result', {}).get('value'):
                print(f"Element '{selector}' found!")
                return True
            time.sleep(0.5)
        
        print(f"Timeout waiting for element '{selector}'")
        return False
        
    finally:
        print("保持标签页打开")


def example_extract_links(url, cdp_port=8080):
    """
    Navigate to URL and extract all links.
    
    Args:
        url (str): Target URL
        cdp_port (int): CDP port
    
    Returns:
        list: List of link URLs
    """
    browser = pychrome.Browser(url=f"http://localhost:{cdp_port}")
    tab = browser.new_tab()
    
    try:
        tab.start()
        tab.Page.enable()
        tab.Runtime.enable()
        
        # Navigate
        tab.Page.navigate(url=url)
        time.sleep(3)
        
        # Extract links
        result = tab.Runtime.evaluate(
            expression="""
            Array.from(document.querySelectorAll('a'))
                .map(a => a.href)
                .filter(href => href)
            """
        )
        
        links = result.get('result', {}).get('value', [])
        print(f"Found {len(links)} links:")
        for i, link in enumerate(links[:10], 1):  # Show first 10
            print(f"  {i}. {link}")
        
        return links
        
    finally:
        print("保持标签页打开")


def example_fill_form(url, form_data, cdp_port=8080):
    """
    Navigate to URL and fill a form.
    
    Args:
        url (str): Target URL
        form_data (dict): Form field selectors and values
        cdp_port (int): CDP port
    
    Example:
        form_data = {
            '#username': 'myuser',
            '#password': 'mypass'
        }
    """
    browser = pychrome.Browser(url=f"http://localhost:{cdp_port}")
    tab = browser.new_tab()
    
    try:
        tab.start()
        tab.Page.enable()
        tab.Runtime.enable()
        
        # Navigate
        tab.Page.navigate(url=url)
        time.sleep(3)
        
        # Fill form fields
        for selector, value in form_data.items():
            js_code = f"""
            (function() {{
                var elem = document.querySelector('{selector}');
                if (elem) {{
                    elem.value = '{value}';
                    return true;
                }}
                return false;
            }})()
            """
            result = tab.Runtime.evaluate(expression=js_code)
            success = result.get('result', {}).get('value', False)
            print(f"Fill '{selector}': {'✓' if success else '✗'}")
        
    finally:
        print("保持标签页打开")


def example_execute_custom_js(url, js_code, cdp_port=8080):
    """
    Navigate to URL and execute custom JavaScript.
    
    Args:
        url (str): Target URL
        js_code (str): JavaScript code to execute
        cdp_port (int): CDP port
    
    Returns:
        Any: Result of JavaScript execution
    """
    browser = pychrome.Browser(url=f"http://localhost:{cdp_port}")
    tab = browser.new_tab()
    
    try:
        tab.start()
        tab.Page.enable()
        tab.Runtime.enable()
        
        # Navigate
        tab.Page.navigate(url=url)
        time.sleep(3)
        
        # Execute JavaScript
        result = tab.Runtime.evaluate(expression=js_code)
        value = result.get('result', {}).get('value')
        
        print(f"JavaScript result: {value}")
        return value
        
    finally:
        print("保持标签页打开")


if __name__ == "__main__":
    # Example usage
    print("=== Example 1: Take Screenshot ===")
    # example_screenshot("https://www.baidu.com")
    
    print("\n=== Example 2: Wait for Element ===")
    # example_wait_for_element("https://www.baidu.com", "#su")
    
    print("\n=== Example 3: Extract Links ===")
    # example_extract_links("https://www.baidu.com")
    
    print("\n=== Example 4: Execute Custom JS ===")
    # example_execute_custom_js(
    #     "https://www.baidu.com",
    #     "document.querySelectorAll('a').length"
    # )
    
    print("\nUncomment examples above to run them.")
