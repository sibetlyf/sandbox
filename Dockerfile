FROM enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest

# 1. 使用 root 安装依赖
USER root
RUN npm install -g pnpm edgeone --force --registry=https://registry.npmmirror.com
