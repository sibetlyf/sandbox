#!/bin/bash
#################################################
# 自动复制脚本
# 功能：将 src 目录下所有子目录的内容复制到 /home/gem
# 特性：
#   - 包括隐藏文件
#   - 强制覆盖同名文件/文件夹
#   - 保留文件权限和属性
#################################################

set -e  # 遇到错误立即退出

# 获取脚本所在目录（即 src 目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/home/gem"

echo "================================================"
echo "开始复制文件到 ${TARGET_DIR}"
echo "源目录: ${SCRIPT_DIR}"
echo "================================================"

# 确保目标目录存在
if [ ! -d "${TARGET_DIR}" ]; then
    echo "错误：目标目录 ${TARGET_DIR} 不存在"
    exit 1
fi

# 启用隐藏文件的 glob 扩展
shopt -s dotglob

# 计数器
total_copied=0
failed=0

# 遍历 src 目录下的所有子目录
for item in "${SCRIPT_DIR}"/*; do
    # 跳过脚本自己
    if [ "$(basename "$item")" == "$(basename "$0")" ]; then
        echo "跳过脚本文件: $(basename "$item")"
        continue
    fi
    
    # 只处理目录
    if [ -d "$item" ]; then
        dir_name="$(basename "$item")"
        echo ""
        echo "正在复制目录: ${dir_name}"
        echo "----------------------------------------"
        
        # 复制目录内容（不是目录本身）
        if cp -rf "${item}/"* "${TARGET_DIR}/" 2>/dev/null; then
            echo "✓ 成功复制: ${dir_name}"
            ((total_copied++))
        else
            # 可能是空目录，检查一下
            if [ -z "$(ls -A "${item}")" ]; then
                echo "⚠ 跳过空目录: ${dir_name}"
            else
                echo "✗ 复制失败: ${dir_name}"
                ((failed++))
            fi
        fi
    else
        # 如果是文件，直接复制到目标目录
        file_name="$(basename "$item")"
        echo ""
        echo "正在复制文件: ${file_name}"
        if cp -f "$item" "${TARGET_DIR}/" 2>/dev/null; then
            echo "✓ 成功复制文件: ${file_name}"
            ((total_copied++))
        else
            echo "✗ 复制文件失败: ${file_name}"
            ((failed++))
        fi
    fi
done

# 恢复默认设置
shopt -u dotglob

echo ""
echo "================================================"
echo "复制完成！"
echo "成功: ${total_copied} 项"
echo "失败: ${failed} 项"
echo "================================================"

# 显示目标目录内容（仅前10项）
echo ""
echo "目标目录 ${TARGET_DIR} 当前内容（前10项）："
ls -la "${TARGET_DIR}" | head -n 12

exit 0
