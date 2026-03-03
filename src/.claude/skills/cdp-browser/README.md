# CDP Browser Control Skill

通过 Chrome DevTools Protocol (CDP) 控制浏览器进行页面导航和内容提取。

## 文件结构

```
cdp-browser/
├── SKILL.md                          # Skill 主文档
├── README.md                         # 本文件
├── scripts/
│   └── navigate_browser.py          # 主导航脚本
└── examples/
    └── advanced_usage.py            # 高级用法示例
```

## 快速开始

### 1. 安装依赖

```bash
pip install pychrome
```

### 2. 启动 CDP 浏览器

确保 Chrome 浏览器以 CDP 模式运行在端口 8080：

```bash
chrome --remote-debugging-port=8080
```

### 3. 使用导航脚本

```bash
# 导航到网页
python scripts/navigate_browser.py --url "https://www.baidu.com"

# 导航到本地应用
python scripts/navigate_browser.py --url "http://localhost:3000"

# 自定义端口和等待时间
python scripts/navigate_browser.py --url "https://example.com" --port 9222 --wait 10

# 提取完整页面内容
python scripts/navigate_browser.py --url "https://example.com" --extract-all
```

## 主要功能

### 基础导航

- ✅ 连接到 CDP 浏览器
- ✅ 导航到指定 URL
- ✅ 提取页面标题
- ✅ 提取当前 URL
- ✅ 提取页面文本内容

### 高级功能（见 examples/advanced_usage.py）

- 📸 截取页面截图
- ⏳ 等待特定元素出现
- 🔗 提取页面所有链接
- 📝 填写表单
- 🔧 执行自定义 JavaScript

## 命令行参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--url` | `-u` | 必填 | 目标 URL |
| `--port` | `-p` | 8080 | CDP 端口 |
| `--wait` | `-w` | 5 | 页面加载等待时间（秒） |
| `--extract-all` | - | False | 提取完整页面文本 |

## 使用示例

### 示例 1: 导航到百度

```bash
python scripts/navigate_browser.py --url "https://www.baidu.com"
```

输出：
```
连接到 CDP 浏览器 (端口 8080)...
正在导航到：https://www.baidu.com
导航结果：{'frameId': '...', 'loaderId': '...'}
等待页面加载 (5 秒)...

=== 页面信息 ===
标题：百度一下，你就知道
URL：https://www.baidu.com/
页面内容预览：
新闻hao123地图贴吧视频图片...

✓ 导航完成，标签页保持打开状态
```

### 示例 2: 测试本地开发服务器

```bash
python scripts/navigate_browser.py --url "http://localhost:3000" --wait 3
```

### 示例 3: 使用不同的 CDP 端口

```bash
python scripts/navigate_browser.py --url "https://example.com" --port 9222
```

## 集成到 Claude 工作流

当用户请求浏览器操作时，Claude 可以：

1. **识别意图**：用户想要打开某个网页
2. **执行脚本**：调用 `navigate_browser.py`
3. **报告结果**：向用户展示页面信息

示例对话：

**用户**: "帮我在浏览器中打开百度首页"

**Claude**: 
```bash
python scripts/navigate_browser.py --url "https://www.baidu.com"
```

已成功导航到百度首页！
- 标题：百度一下，你就知道
- URL：https://www.baidu.com/

## 常见问题

### Q: 出现 "Connection refused" 错误

**A**: 确保 Chrome 浏览器已启动并开启 CDP：
```bash
chrome --remote-debugging-port=8080
```

### Q: 出现 "ModuleNotFoundError: No module named 'pychrome'"

**A**: 安装 pychrome：
```bash
pip install pychrome
```

### Q: 页面加载不完整

**A**: 增加等待时间：
```bash
python scripts/navigate_browser.py --url "..." --wait 10
```

### Q: 关闭标签页时出现 JSON 解码错误

**A**: 这是 pychrome 的已知问题，不影响功能。脚本已移除清理代码，保持标签页打开。

## 进阶使用

查看 `examples/advanced_usage.py` 了解：

- 如何截取页面截图
- 如何等待特定元素
- 如何提取页面链接
- 如何填写表单
- 如何执行自定义 JavaScript

## 技术细节

- **协议**: Chrome DevTools Protocol (CDP)
- **Python 库**: pychrome
- **支持的浏览器**: Chrome, Chromium, Edge (Chromium-based)
- **默认端口**: 8080

## 许可证

MIT License
