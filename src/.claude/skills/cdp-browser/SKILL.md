---
name: CDP Browser Control
description: Control Chrome DevTools Protocol browser to navigate pages and extract content
---

# CDP Browser Control Skill

This skill enables you to control a Chrome browser via Chrome DevTools Protocol (CDP) to navigate to URLs and extract page content.

## Prerequisites

- A Chrome browser running with CDP enabled on port 8080
- Python environment with `pychrome` package installed

## Usage

When you need to control a browser via CDP, use the provided script to:
1. Navigate to any URL
2. Extract page title, URL, and content
3. Execute JavaScript in the page context

### Input Parameters

- **url**: The target URL to navigate to (required)
- **cdp_port**: CDP port (default: 8080)
- **wait_time**: Time to wait for page load in seconds (default: 5)

### How to Use This Skill

**Step 1: Ensure CDP Browser is Running**

Verify that a Chrome browser is running with CDP enabled on the specified port (default: 8080).

**Step 2: Execute the Navigation Script**

Use the `navigate_browser.py` script in the `scripts/` directory:

```bash
python scripts/navigate_browser.py --url "https://example.com" --port 8080 --wait 5
```

**Step 3: Process the Output**

The script will output:
- Navigation result (frameId and loaderId)
- Page title
- Current URL
- Page content preview (first 300 characters)

### Example Interactions

**Example 1: Navigate to a website**

```bash
python scripts/navigate_browser.py --url "https://www.baidu.com"
```

Output:
```
连接到 CDP 浏览器...
正在导航到：https://www.baidu.com
导航结果：{'frameId': '...', 'loaderId': '...'}
等待页面加载...

=== 页面信息 ===
标题：百度一下，你就知道
URL：https://www.baidu.com/
页面内容预览：...
```

**Example 2: Navigate to localhost application**

```bash
python scripts/navigate_browser.py --url "http://localhost:3000" --wait 3
```

**Example 3: Custom CDP port**

```bash
python scripts/navigate_browser.py --url "https://example.com" --port 9222
```

## Script Parameters

The `navigate_browser.py` script accepts the following command-line arguments:

- `--url` or `-u`: Target URL (required)
- `--port` or `-p`: CDP port (default: 8080)
- `--wait` or `-w`: Wait time in seconds (default: 5)
- `--extract-all`: Extract full page text instead of preview

## Advanced Usage

### Custom JavaScript Execution

You can modify the script to execute custom JavaScript:

```python
# Execute custom JavaScript
result = tab.Runtime.evaluate(expression="document.querySelectorAll('a').length")
link_count = result.get('result', {}).get('value', 0)
print(f"页面链接数：{link_count}")
```

### Taking Screenshots

```python
# Enable Page domain
tab.Page.enable()

# Capture screenshot
screenshot = tab.Page.captureScreenshot(format='png')
with open('screenshot.png', 'wb') as f:
    import base64
    f.write(base64.b64decode(screenshot['data']))
```

### Waiting for Specific Elements

```python
# Wait for element to appear
import time
timeout = 10
start = time.time()
while time.time() - start < timeout:
    result = tab.Runtime.evaluate(expression="document.querySelector('#myElement') !== null")
    if result.get('result', {}).get('value'):
        print("Element found!")
        break
    time.sleep(0.5)
```

## Error Handling

### Common Issues

1. **Connection refused**: Ensure Chrome is running with CDP enabled
   ```bash
   chrome --remote-debugging-port=8080
   ```

2. **Module not found**: Install pychrome
   ```bash
   pip install pychrome
   ```

3. **Page load timeout**: Increase wait time with `--wait` parameter

4. **JSON decode error**: This is a known issue with pychrome when closing tabs. The script completes successfully despite this error.

## Integration with Claude

When using this skill in conversations:

1. **User requests browser navigation**: "打开百度首页"
   
   **Your action**: Execute the script with appropriate URL
   ```bash
   python scripts/navigate_browser.py --url "https://www.baidu.com"
   ```

2. **User wants to test their local app**: "在浏览器中打开 localhost:3000"
   
   **Your action**: Navigate to local URL
   ```bash
   python scripts/navigate_browser.py --url "http://localhost:3000"
   ```

3. **User needs page content**: "获取这个页面的内容"
   
   **Your action**: Use the script and report the extracted content

## Notes

- The browser tab remains open after navigation (cleanup code is commented out)
- Page load wait time is fixed; consider implementing event-based waiting for production use
- The script creates a new tab for each execution
- Some websites may block automated access or require additional handling (cookies, authentication, etc.)

## Files in This Skill

- `SKILL.md`: This documentation file
- `scripts/navigate_browser.py`: Main navigation script
- `examples/advanced_usage.py`: Advanced usage examples
