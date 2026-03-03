#!/bin/bash
# deploy.sh

set -e

# ==============================================================================
# 默认端口映射 (对应 docker-compose 中暴露的端口)
# ==============================================================================
HOST_PORT=${HOST_PORT:-9020}      # 映射 8080 (MOMA UI)
FRONTEND_PORT=${FRONTEND_PORT:-8081} # 映射 30001 (Next.js Frontend)
SPACE_PORT=${SPACE_PORT:-8085}    # 映射 10086 (Space)

IMAGE_NAME="aio-sandbox-image"
CONTAINER_NAME="aio-sandbox_run"

# ==============================================================================
# 帮助文档
# ==============================================================================
show_help() {
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  -n, --name <name>      指定自定义容器名称 (默认: $CONTAINER_NAME)"
    echo "  -p8080 <port>          覆盖映射到容器 8080 端口的主机端口 (默认: $HOST_PORT)"
    echo "  -p30001 <port>         覆盖映射到容器 30001 端口的主机端口 (默认: $FRONTEND_PORT)"
    echo "  -p10086 <port>         覆盖映射到容器 10086 端口的主机端口 (默认: $SPACE_PORT)"
    echo "  -h, --help             显示此帮助信息"
    exit 0
}

# ==============================================================================
# 解析参数
# ==============================================================================
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -n|--name) CONTAINER_NAME="$2"; shift ;;
        -p8080) HOST_PORT="$2"; shift ;;
        -p30001) FRONTEND_PORT="$2"; shift ;;
        -p10086) SPACE_PORT="$2"; shift ;;
        -h|--help) show_help ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
    shift
done

echo "================================================"
echo "1. 构建 Docker 镜像..."
echo "================================================"
docker build -t "$IMAGE_NAME" .

echo "================================================"
echo "启动容器，重定义端口映射..."
echo "================================================"
# 运行参数中重定义了各个映射端口 (同步自 docker-compose.yaml)
docker run -d \
    --name "$CONTAINER_NAME" \
    --security-opt seccomp=unconfined \
    --shm-size="2gb" \
    --memory="8g" \
    --cpus="4" \
    --add-host="host.docker.internal:host-gateway" \
    -p "${HOST_PORT}:8080" \
    -p "${FRONTEND_PORT}:30001" \
    -p "${SPACE_PORT}:10086" \
    -e XMODIFIERS="@im=fcitx" \
    -e QT_IM_MODULE="fcitx" \
    -e GTK_IM_MODULE="fcitx" \
    "$IMAGE_NAME"

echo "等待容器初始化 (5秒)..."
sleep 5

echo "================================================"
echo "2. 将 1.sh 复制并执行直到完成..."
echo "================================================"
docker cp 1.sh "$CONTAINER_NAME":/home/gem/1.sh
docker exec -u root "$CONTAINER_NAME" chown gem:gem /home/gem/1.sh
docker exec -u gem "$CONTAINER_NAME" bash /home/gem/1.sh

echo "================================================"
echo "3. 将 src 中所有内容强行复制到容器 gem 用户下..."
echo "================================================"
# docker cp 复制目录到内部
docker cp src/. "$CONTAINER_NAME":/home/gem/
# 再次统一赋予 gem 用户权限
docker exec -u root "$CONTAINER_NAME" chown -R gem:gem /home/gem/

echo "================================================"
echo "4. 启动后端与前端服务 (并行)..."
echo "================================================"
echo "正在容器内配置环境并并行启动服务 (detached 模式)..."
# 使用 -d 触发 run.sh 逻辑
docker exec -d -u gem "$CONTAINER_NAME" bash /home/gem/run.sh

echo "================================================"
echo "🎉 所有操作圆满完成！"
echo "容器名称: $CONTAINER_NAME"
echo "服务已在容器后台启动。你可以通过以下命令查看实时日志："
echo "docker exec $CONTAINER_NAME tail -f /home/gem/logs/backend.log"
echo "docker exec $CONTAINER_NAME tail -f /home/gem/logs/frontend.log"
echo "================================================"
