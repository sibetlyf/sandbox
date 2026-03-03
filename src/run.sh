#!/bin/bash

# 1. 准备环境 (此时以 gem 用户运行)
cd "$(dirname "$0")"
mkdir -p logs
# 清理旧日志以确保重新检测
> logs/backend.log
> logs/frontend.log

# 检查并清理端口
kill_port() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        pid=$(lsof -t -i:$port)
        [ -n "$pid" ] && kill -9 $pid 2>/dev/null
    fi
}
kill_port 30000
kill_port 30001
[ -f "frontend/.next/dev/lock" ] && rm -f "frontend/.next/dev/lock"

echo "🚀 [Gem] 正在以后台守护模式启动双端服务..."

# 3. 启动后端 (service.py)
nohup bash -c "
    echo \"🐍 [Backend] 正在安装 Python 依赖库...\"
    pip3 install -r backend/requirements.txt --quiet --user -i https://pypi.tuna.tsinghua.edu.cn/simple || echo \"❌ [Backend] pip install 失败\"
    echo \"🐍 [Backend] 启动服务 (Port: 30000)...\"
    export PORT=30000
    python3 -u backend/service.py 2>&1 | tee logs/backend.log
" > logs/backend_nohup.out 2>&1 &

# 4. 启动前端 (Next.js)
nohup bash -c "
    echo \"⚛️  [Frontend] 正在准备环境...\"
    if [ ! -d \"frontend/node_modules\" ]; then
        echo \"⚛️  [Frontend] 正在安装 npm 依赖 (可能需要 1-3 分钟)...\"
        npm install --prefix frontend --registry=https://registry.npmmirror.com || echo \"❌ [Frontend] npm install 失败\"
    fi
    echo \"⚛️  [Frontend] 启动 dev server (Port: 30001)...\"
    npm run dev --prefix frontend 2>&1 | tee logs/frontend.log
" > logs/frontend_nohup.out 2>&1 &

# 5. 等待服务就绪监控
echo "⏳ 正在等待后端和前端服务就绪..."
BACKEND_READY=false
FRONTEND_READY=false

for i in {1..300}; do  # 最多等待 5 分钟
    if ! $BACKEND_READY && grep -q "启动WebSocket服务" logs/backend.log; then
        echo "✅ [Backend] 后端服务已就绪！"
        BACKEND_READY=true
    fi
    if ! $FRONTEND_READY && grep -q "Ready in" logs/frontend.log; then
        echo "✅ [Frontend] 前端服务已就绪！"
        FRONTEND_READY=true
    fi

    if $BACKEND_READY && $FRONTEND_READY; then
        echo "🎉 所有服务均已成功启动！"
        exit 0
    fi
    
    # 打印安装进度预览，让用户知道在做什么
    if [ $((i % 10)) -eq 0 ]; then
        echo "正在构建中... (已等待 ${i}s)"
    fi
    sleep 1
done

echo "❌ 部署超时，请检查 logs/ 目录下的日志。"
exit 1
