# MOMA Sandbox

这是一个定制化的智能体沙盒环境，集成了浏览器自动化、代码执行和多平台解析能力。本项目旨在为 AI Agent 提供一个安全、高效且易于扩展的执行环境。

## 🌟 主要特性

- **浏览器自动化**: 集成 Playwright/Chromium，支持远程 VNC 访问和 CDP 控制。
- **多平台适配**: 内置 Jiutian 和 OpenCode 协议解析器，无缝对接多种大模型平台。
- **全栈架构**: 
  - **Backend**: 基于 Python/FastAPI 的后端服务，处理浏览器控制、文件操作及会话管理。
  - **Frontend**: 基于 Next.js + Tailwind CSS 的现代化管理后台。
- **灵活部署**: 支持 Docker 一键部署及多级环境配置。

## � 项目结构

```text
.
├── backend/          # Python 后端服务逻辑
├── frontend/         # Next.js 前端应用
├── sdk/              # 与沙盒交互的 SDK (Python, TS, Go)
├── website/          # 文档及演示网页
├── docker/           # Docker 配置文件
├── scripts/          # 运维及辅助脚本
└── deploy.sh         # 一键部署脚本
```

## � 快速开始

### 1. 环境准备

确保您的系统中已安装以下工具：
- Docker & Docker Compose
- Node.js (用于前端开发)
- Python 3.10+ (用于后端开发)

### 2. 部署

使用根目录下的部署脚本：

```bash
# 赋予执行权限
chmod +x deploy.sh

# 启动服务
./deploy.sh
```

或者使用 Docker Compose 手动启动：

```bash
docker-compose up -d
```

### 3. 开发模式

#### 后端
```bash
cd src/backend
pip install -r requirements.txt
python service.py
```

#### 前端
```bash
cd src/frontend
pnpm install
pnpm dev
```

## 🔌 API & 协议

沙盒提供了丰富的 RESTful API，详细文档通常可在服务启动后访问：
- API 文档: `http://localhost:8080/v1/docs`

## 🤝 贡献规范

欢迎提交 Pull Request 或报告 Issue。

## 📄 开源协议

本项目采用 [Apache License 2.0](LICENSE) 开源协议。
