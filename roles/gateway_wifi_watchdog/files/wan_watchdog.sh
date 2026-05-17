#!/bin/sh
# v2

WAN_IFACE="phy0-sta0"
INTERVAL=10
THRESHOLD=3

fail_count=0
success_count=0
ap_active=0

ap_up() {
    uci set wireless.radio1.disabled='0'
    uci commit wireless
    wifi up radio1
    sleep 3
    ap_active=1
    logger -t wan_watchdog "WAN down, AP enabled"
}

ap_down() {
    uci set wireless.radio1.disabled='1'
    uci commit wireless
    wifi down radio1
    sleep 3
    ap_active=0
    logger -t wan_watchdog "WAN restored, AP disabled"
}

while true; do
    if ip addr show "$WAN_IFACE" | grep -q 'inet '; then
        fail_count=0
        if [ "$ap_active" = "1" ]; then
            success_count=$((success_count + 1))
            if [ "$success_count" -ge "$THRESHOLD" ]; then
                ap_down
                success_count=0
            fi
        fi
    else
        success_count=0
        if [ "$ap_active" = "0" ]; then
            fail_count=$((fail_count + 1))
            if [ "$fail_count" -ge "$THRESHOLD" ]; then
                ap_up
                fail_count=0
            fi
        fi
    fi
    sleep "$INTERVAL"
done
