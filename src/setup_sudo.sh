#!/bin/bash

# 检查是否以 root 身份运行
if [ "$(id -u)" != "0" ]; then
   echo "错误: 此脚本必须以 root 身份运行" 1>&2
   exit 1
fi

USERNAME="gem"

# 检查用户是否存在
if id "$USERNAME" &>/dev/null; then
    echo "✅ 用户 $USERNAME 已存在"
else
    echo "⚠️ 用户 $USERNAME 不存在，正在创建..."
    useradd -m -s /bin/bash "$USERNAME"
fi

# 配置 sudo 免密权限
# 使用 /etc/sudoers.d/ 目录是更安全和推荐的做法，避免直接修改 /etc/sudoers 文件
SUDO_FILE="/etc/sudoers.d/$USERNAME"

echo "正在配置 sudo 权限..."
echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" > "$SUDO_FILE"

# 设置正确的文件权限 (必须是 0440)
chmod 0440 "$SUDO_FILE"

echo "🎉 成功！用户 $USERNAME 现在可以使用 sudo 且无需输入密码。"
