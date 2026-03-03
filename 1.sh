#!/bin/bash

# 定义颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}>>> 阶段 1: 配置 npm 全局环境...${NC}"

# 1. 创建目录
NPM_GLOBAL_DIR="$HOME/.npm-global"
mkdir -p "$NPM_GLOBAL_DIR"

# 2. 配置 npm
npm config set prefix "$NPM_GLOBAL_DIR"
echo -e "${GREEN}√ npm prefix 已设置为 $NPM_GLOBAL_DIR${NC}"

# 3. 持久化 PATH 到配置文件
CURRENT_SHELL=$(basename "$SHELL")
TARGET_FILE=""
EXPORT_CMD="export PATH=\"$NPM_GLOBAL_DIR/bin:\$PATH\""

case "$CURRENT_SHELL" in
    bash) TARGET_FILE="$HOME/.bashrc" ;;
    zsh)  TARGET_FILE="$HOME/.zshrc" ;;
    fish) 
        TARGET_FILE="$HOME/.config/fish/config.fish"
        EXPORT_CMD="set -gx PATH $NPM_GLOBAL_DIR/bin \$PATH"
        ;;
    *)    echo -e "${YELLOW}未知 Shell，跳过配置文件自动写入。${NC}" ;;
esac

if [ -n "$TARGET_FILE" ]; then
    if grep -q ".npm-global/bin" "$TARGET_FILE"; then
        echo -e "${YELLOW}√ 配置文件已包含路径，跳过写入。${NC}"
    else
        echo "" >> "$TARGET_FILE"
        echo "# NPM Global Path" >> "$TARGET_FILE"
        echo "$EXPORT_CMD" >> "$TARGET_FILE"
        echo -e "${GREEN}√ 已更新配置文件: $TARGET_FILE${NC}"
    fi
fi

# 4. 关键步骤：在当前脚本中临时应用 PATH
# 这样后续安装的 npm 包可以直接被识别（虽然 npm install 无论 path 均可安装，但这样更稳健）
export PATH="$NPM_GLOBAL_DIR/bin:$PATH"

echo -e "\n${BLUE}>>> 阶段 3: 安装 npm 全局工具包...${NC}"
echo -e "${YELLOW}正在安装 @anthropic-ai/claude-code...${NC}"
npm install -g @anthropic-ai/claude-code
echo -e "${YELLOW}正在安装 @musistudio/claude-code-router...${NC}"
npm install -g @musistudio/claude-code-router

# echo -e "${YELLOW}正在安装 opencode-ai...${NC}"
# npm install -g opencode-ai

echo -e "\n-------------------------------------------------------"
echo -e "${GREEN}所有任务执行完毕！${NC}"
echo -e "请务必执行以下命令刷新当前终端环境："
echo -e ""
echo -e "    ${YELLOW}source $TARGET_FILE${NC}"
echo -e ""
echo -e "验证安装："
echo -e "    claude --version"
echo -e "    which claude-code-router" 
echo -e "-------------------------------------------------------"