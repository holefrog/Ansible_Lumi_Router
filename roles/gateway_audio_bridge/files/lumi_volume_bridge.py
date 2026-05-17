#!/usr/bin/env python3
import json
import subprocess
import time
import re
import os
import paho.mqtt.client as mqtt

# ==================== 核心配置区域 ====================
MQTT_HOST = "192.168.50.236"
MQTT_PORT = 1883
MQTT_USER = "mqtt-user"
MQTT_PASS = "mqtt-user"
# ======================================================

def get_dynamic_device_id():
    """动态捕获 OpenWrt 当前网卡的真实物理 MAC 地址，实现多机自适应且零配置污染"""
    for iface in ['wlan0', 'wlan0-1', 'eth0', 'br-lan']:
        path = f"/sys/class/net/{iface}/address"
        if os.path.exists(path):
            with open(path, "r") as f:
                mac = f.read().strip().replace(":", "").lower()
                if mac:
                    return f"0x{mac}"
    return "0x7c49eb93b068"  # 终极保底兜底

DEVICE_ID = get_dynamic_device_id()

TOPIC_SNAP_SET = f"lumi/{DEVICE_ID}/volumesnap/set"
TOPIC_SNAP_STATE = f"lumi/{DEVICE_ID}/volumesnap/state"
TOPIC_ALERT_SET = f"lumi/{DEVICE_ID}/volumealert/set"
TOPIC_ALERT_STATE = f"lumi/{DEVICE_ID}/volumealert/state"

DISCO_SNAP = f"homeassistant/number/{DEVICE_ID}/volumesnap/config"
DISCO_ALERT = f"homeassistant/number/{DEVICE_ID}/volumealert/config"

def get_hardware_volume(channel):
    try:
        res = subprocess.run(["amixer", "sget", channel], capture_output=True, text=True)
        match = re.search(r'\[(\d+)%\]', res.stdout)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 50

def send_ha_discovery(client):
    device_info = {
        "identifiers": [f"xiaomi_gateway_{DEVICE_ID}"],
        "name": f"xiaomi_gateway_{DEVICE_ID}",
        "sw_version": "1.0.18",
        "model": "Xiaomi Gateway",
        "manufacturer": "Xiaomi"
    }

    snap_payload = {
        "name": "Playback Volume",
        "unique_id": f"lumi_{DEVICE_ID}_volumesnap",
        "state_topic": TOPIC_SNAP_STATE,
        "command_topic": TOPIC_SNAP_SET,
        "min": 0,
        "max": 100,
        "step": 1,
        "icon": "mdi:volume-high",
        "device": device_info
    }

    alert_payload = {
        "name": "Alert Volume",
        "unique_id": f"lumi_{DEVICE_ID}_volumealert",
        "state_topic": TOPIC_ALERT_STATE,
        "command_topic": TOPIC_ALERT_SET,
        "min": 0,
        "max": 100,
        "step": 1,
        "icon": "mdi:bell",
        "device": device_info
    }

    client.publish(DISCO_SNAP, json.dumps(snap_payload), retain=True)
    client.publish(DISCO_ALERT, json.dumps(alert_payload), retain=True)
    client.publish(TOPIC_SNAP_STATE, str(get_hardware_volume("Master")), retain=True)
    client.publish(TOPIC_ALERT_STATE, str(get_hardware_volume("AlertVol")), retain=True)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(TOPIC_SNAP_SET)
        client.subscribe(TOPIC_ALERT_SET)
        send_ha_discovery(client)

def on_message(client, userdata, msg):
    try:
        val = int(float(msg.payload.decode()))
        if msg.topic == TOPIC_SNAP_SET:
            subprocess.run(["amixer", "sset", "Master", f"{val}%"], stdout=subprocess.DEVNULL)
            client.publish(TOPIC_SNAP_STATE, str(val), retain=True)
        elif msg.topic == TOPIC_ALERT_SET:
            subprocess.run(["amixer", "sset", "AlertVol", f"{val}%"], stdout=subprocess.DEVNULL)
            client.publish(TOPIC_ALERT_STATE, str(val), retain=True)
    except Exception:
        pass

def main():
    client = mqtt.Client()
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_forever()
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    main()
