#!/bin/bash
# 测试后端服务存活状态 (Health Check)
# 注意: service.py 是 WebSocket 服务，不支持 curl 直接发送问题 (Chat)

# 1. 检查后端 (宿主机端口 8084 -> 容器 9999)
echo "Running Backend check..."
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8084/health && echo " ✅  Backend (8084) is UP" || echo " ❌  Backend (8084) is DOWN"

# 2. 检查前端
echo "Running Frontend check..."
# Check port 8081 (Mapped to container 3000)
if curl -s -I http://127.0.0.1:8081 >/dev/null; then
    echo " ✅  Frontend (8081) is UP"
# Check port 8082 (Mapped to container 3001)
elif curl -s -I http://127.0.0.1:8082 >/dev/null; then
    echo " ✅  Frontend (8082) is UP"  # Next.js fallback port
else
    echo " ❌  Frontend is DOWN (Checked 8081 & 8082)"
fi
echo ""
