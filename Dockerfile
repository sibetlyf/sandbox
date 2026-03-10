# syntax=docker/dockerfile:1
FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest

# 1. 使用 root 安装依赖
USER root
RUN npm install -g pnpm edgeone --force --registry=https://registry.npmmirror.com
RUN npm install -g @anthropic-ai/claude-code @musistudio/claude-code-router

# 2. 创建 CCR 所需的配置目录和插件目录
RUN mkdir -p /root/.claude-code-router/plugins

# 4. 写入 settings.json (使用现代 Here-Docs 语法)
COPY <<EOF /root/.claude-code-router/config.json
{
  "PORT": 3459,
  "LOG": true,
  "LOG_LEVEL": "trace",
  "Providers": [
    {
      "name": "jiutian",
      "api_base_url": "https://jiutian.10086.cn/largemodel/moma/api/v3/chat/completions",
      "api_key": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJhcGlfa2V5IjoiNjkzMDFlN2NiODE5YWIwMGZkYjYxYjUxIiwiZXhwIjoxODU1NDQzNTE4NjIwNTEsInRpbWVzdGFtcCI6MTc2NDc2MTI1MX0.VJ68I58MyV4xeSVYnM7-E6MimYimGrd0PA3U40yJfQE",
      "models": ["kimi-k2-5-thinking", "glm-5-fp8", "qwen3.5-397B-fp8", "jiutian-lan-35b"],
      "transformer": { "use": ["openrouter"] }
    }
  ],
  "Router": {
    "default": "jiutian,qwen3.5-397B-fp8",
    "longContextThreshold": 160000
  }
}
EOF

# 5. 配置全局环境变量
ENV ANTHROPIC_BASE_URL="http://127.0.0.1:3459"
ENV ANTHROPIC_API_KEY="sk-ant-placeholder"

# 6. 设置启动入口
RUN ccr restart
