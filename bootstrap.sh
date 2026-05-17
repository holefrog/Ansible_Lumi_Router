#!/bin/bash

echo "=================================================="
echo "      OpenWrt 智能网关初始化 (Bootstrap) 工具     "
echo "=================================================="
echo ""
echo "⚠️  准备工作："
echo "请先手动将电脑 Wi-Fi 连接到刚刷好固件的 OpenWrt 路由器。"
echo "默认目标 IP 为：192.168.1.1"
echo ""
read -p "确认已连接 OpenWrt Wi-Fi 后，请按 [回车键] 继续..."

echo ""
echo "🚀 开始推送初始配置..."
# -k 参数会提示输入密码，如果是全新无密码固件，提示 SSH password 时直接按回车即可
ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i '192.168.1.1,' -u root -k bootstrap.yml