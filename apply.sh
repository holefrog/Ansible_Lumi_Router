#!/bin/bash
set -euo pipefail

# apply.sh 仅用于正常生产环境部署/更新。
# - Use bootstrap.sh for fresh OpenWrt initialization on 192.168.1.1.
# - Use apply.sh for site.yml/status.yml deployments using inventories/production.yml.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "--------------------------------------------------------"
echo "🚀 Lumi Router 一体化部署与管理系统"
echo "--------------------------------------------------------"
echo "1) Deploy      - 执行完整部署 (site.yml)"
echo "2) Status      - 检查服务状态 (status.yml)"
echo "--------------------------------------------------------"
read -rp "请选择 [1/2，其他退出]: " choice

case "$choice" in
    1)
        MODE="Deploy"
        PB="site.yml"
        ;;
    2)
        MODE="Status"
        PB="status.yml"
        ;;
    *)
        echo "已退出。"
        exit 0
        ;;
esac

echo ">>> 已选择: ${MODE}"
echo ""

VERBOSE=""
read -rp "是否开启详细输出 verbose？[y/N]: " v
if [[ "$v" =~ ^[Yy]$ ]]; then
    VERBOSE="-v"
fi
echo ""

# 提示: OpenWrt 默认直接用 root 运行，通常不需要 become 提权密码。
# 仅当您使用了非 root 用户登录并需要提权时才选 Y。
BECOME_PASS=""
read -rp "是否需要输入 sudo 密码 (用于 become)？[y/N]: " bp
if [[ "$bp" =~ ^[Yy]$ ]]; then
    BECOME_PASS="-K"
fi
echo ""

echo "--------------------------------------------------------"
echo "🛠️  正在执行 ${MODE}..."
echo "--------------------------------------------------------"

ansible-playbook "$PB" $VERBOSE $BECOME_PASS "$@"

echo ""
echo "🎉 ${MODE} 完成！"