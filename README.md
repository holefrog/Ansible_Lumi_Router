# ZHWG11LM (Aqara Hub v1) 全套玩机终极指南：从获取 Root 到全面接入 Home Assistant

本指南适用于将绿米网关 **ZHWG11LM (Aqara Hub)** 彻底解锁，空中刷入 OpenWrt 系统，将板载 JN5169 芯片配置为通用的 Zigbee Router（中继器），并最终通过 MQTT 将网关原厂硬件（RGB 夜灯、物理按键、光照传感器、音量调音台与喇叭）全面桥接融入 Home Assistant 智能家居生态。

---

## 目录

- [第一部分：获得 Root 权限并创建 SSH 服务器](#第一部分获得-root-权限并创建-ssh-服务器)
- [第二部分：备份原厂固件（原厂 SSH 环境）](#第二部分备份原厂固件原厂-ssh-环境)
- [第三部分：空中刷入 OpenWrt 系统 (OTA)](#第三部分空中刷入-openwrt-系统-ota)
- [第四部分：配置 OpenWrt 网络环境](#第四部分配置-openwrt-网络环境)
- [第五部分：刷写 JN5169 芯片为 Zigbee Router 模式](#第五部分刷写-jn5169-芯片为-zigbee-router-模式)
- [第六部分：接入智能家居平台 (ZHA / Zigbee2MQTT)](#第六部分接入智能家居平台-zha--zigbee2mqtt)
- [第七部分：恢复纯净 OpenWrt 出厂默认状态](#第七部分恢复纯净-openwrt-出厂默认状态)
- [第八部分：全面激活并集成原有 Hub 硬件外设 (MQTT)](#第八部分全面激活并集成原有-hub-硬件外设-mqtt)
- [第九部分：音频功能控制与进阶玩耍指南](#第九部分音频功能控制与进阶玩耍指南)
- [第十部分：批量部署与灾备（Ansible 自动化）](#第十部分批量部署与灾备ansible-自动化)
- [附录：物理按键复位速查](#附录物理按键复位速查)

---

## 第一部分：获得 Root 权限并创建 SSH 服务器

- **参考文档：** https://openlumi.github.io/gain_root.html
- **默认参考 Root 凭据：** `uHqZ3P9k`

### 1.1 中断启动引导

1. 使用 **115200** 波特率连接网关的硬件串口（UART）。
2. 在设备上电后的瞬间，立即在串口终端中频繁按下**任意键**以阻止系统继续引导。
3. 若终端没有停在 `=>` 提示符处，说明未能成功中断。请拔掉网关电源重新插上并重复。

### 1.2 获取临时 Root 权限

在引导提示符 `=>` 后输入以下命令并回车，以单用户读写模式挂载并启动系统内核：

```bash
setenv bootargs "${bootargs} single rw init=/bin/bash" && boot
```

### 1.3 修改 Root 密码

进入系统后输入修改密码命令，连续按下 **3 次回车键**，root 密码将被设置为空：

```bash
passwd
```

### 1.4 启用 SSH 服务

使用 vi 编辑器打开文件，在 `/home/root/fac/fac_test` 行的**前面**精准添加启动脚本：

```bash
vi /etc/rc.local
```

添加内容：

```text
/etc/init.d/dropbear start &
```

### 1.5 保存并重启

```bash
sync
```

将网关断电，然后重新上电正常启动。

---

### 常见错误：SSH 连接被拒绝

收到如下错误时：

```text
Starting Dropbear SSH server: Pseudo-terminal will not be allocated because stdin is not a terminal.
ssh: connect to host rsa port 22: Connection refused
```

原因是原厂 dropbear 固件编译时未包含 SSH Server 功能，需替换为完整版。

#### 步骤一：登录正常系统的控制台

开机滚屏结束后，输入 `exit_factory` 回车退出测试模式，在 `login:` 提示符处输入 `root`（密码直接回车）进入完整 Linux 环境。

#### 步骤二：建立功能完整的 SSH Server

```bash
# 注入公共 DNS
echo "nameserver 8.8.8.8" > /etc/resolv.conf

# 测试外网连通（Ctrl+C 退出）
ping -c 3 raw.githubusercontent.com

# 备份原厂阉割版
mv /usr/sbin/dropbearmulti /usr/sbin/dropbearmulti.backup

# 下载完整版
echo -e "GET /openlumi/openlumi.github.io/master/files/dropbearmulti HTTP/1.0\nHost: raw.githubusercontent.com\n" > /tmp/request.txt
openssl s_client -quiet -connect raw.githubusercontent.com:443 -servername raw.githubusercontent.com < /tmp/request.txt > /tmp/raw_response.txt

# 验证文件大小不为 0
ls -l /tmp/raw_response.txt

# 提取二进制
sed '1,/^\r$/d' /tmp/raw_response.txt > /usr/sbin/dropbearmulti

# 赋权并建立软链接
chmod +x /usr/sbin/dropbearmulti
ln -sf /usr/sbin/dropbearmulti /usr/sbin/dropbear

# 启动 SSH
/etc/init.d/dropbear start
```

> 注意：下载过程中出现 `verify error:num=20:unable to get local issuer certificate` 属正常现象，不影响下载。

#### 步骤三：连接测试

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa root@192.168.50.234
```

---

## 第二部分：备份原厂固件（原厂 SSH 环境）

每个网关的官方证书、密钥、MAC 地址均唯一，**严禁跳过备份步骤**，丢失后设备将永久无法连接绿米云端或恢复原厂。

### 2.1 轻量密钥备份（备份至云端文本流）

```bash
cd /lumi/conf/
for fn in *; do printf "=== Start $fn ===\n"; cat "$fn"; printf "=== End $fn ===\n"; done | nc termbin.com 9999
```

命令执行后会输出一个 `http://termbin.com/xxxx` 的 URL，在浏览器中打开，将全部内容保存到本地 txt 文件。

### 2.2 完整系统备份（打包根目录）

在网关 SSH 终端执行（约需 5 分钟）：

```bash
tar -cvpzf /tmp/lumi_stock.tar.gz -C / . --exclude='./tmp/*' --exclude='./proc/*' --exclude='./sys/*'
```

在本地电脑终端拉取备份：

```bash
scp -O -o HostKeyAlgorithms=+ssh-rsa root@192.168.50.234:/tmp/lumi_stock.tar.gz .
```

---

## 第三部分：空中刷入 OpenWrt 系统 (OTA)

### 3.1 执行一键刷机脚本

确保网关已正常联网，在原厂 SSH 终端执行：

```bash
echo -e "GET /openlumi/owrt-installer/main/install.sh HTTP/1.0\nHost: raw.githubusercontent.com\n" | openssl s_client -quiet -connect raw.githubusercontent.com:443 -servername raw.githubusercontent.com 2>/dev/null | sed '1,/^\r$/d' | bash
```

**预期现象：** 脚本运行后会强制终止所有 lumi 官方业务进程，**SSH 连接会立即断开**，这是完全正常的。

**耐心等待 3 至 5 分钟**，期间绝对不能断电。

---

## 第四部分：配置 OpenWrt 网络环境

刷写成功后，网关会作为运行 OpenWrt 系统的微型路由器默认发射无线信号。

### 4.1 连接网关初始 Wi-Fi

1. 连接名为 **OpenWrt** 的无密码开放 Wi-Fi。
2. 浏览器访问 `http://192.168.1.1` 进入 LuCI 界面。
3. 用户名 `root`，**密码为空**，直接点击 **Login**。
4. 建议立即修改 root 密码为 `uHqZ3P9k`。

### 4.2 桥接至家里主路由的 Wi-Fi 网络

> ⚠️ **排坑警告**：由于无线芯片驱动限制，LuCI 网页操作极易导致无线芯片在 AP/STA 模式切换间死锁，**强烈推荐使用命令行方法**。

#### 【方法：手动修改无线配置文件（推荐 🌟）】

SSH 登录网关：

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa root@192.168.1.1
```

**修改 `/etc/config/wireless`：**

```bash
mv /etc/config/wireless /etc/config/wireless.bak
vi /etc/config/wireless
```

写入以下内容（`ssid` 与 `key` 按实际修改）：

```
config wifi-device 'radio0'
	option type 'mac80211'
	option path 'platform/soc/2100000.bus/2190000.mmc/mmc_host/mmc0/mmc0:0001/mmc0:0001:1'
	option band '2g'
	option channel 'auto'
	option htmode 'NOHT'

config wifi-iface 'router_client'
	option device 'radio0'
	option network 'wan'
	option mode 'sta'
	option ssid '5300'
	option encryption 'psk2'
	option key 'David@Home'

config wifi-device 'radio1'
	option type 'mac80211'
	option path 'platform/soc/2100000.bus/2190000.mmc/mmc_host/mmc0/mmc0:0001/mmc0:0001:1+1'
	option band '2g'
	option channel '1'
	option htmode 'NOHT'
	option disabled '1'

config wifi-iface 'default_radio1'
	option device 'radio1'
	option network 'lan'
	option mode 'ap'
	option ssid 'OpenWrt'
	option encryption 'none'
```

**修改 `/etc/config/network`：**

```bash
mv /etc/config/network /etc/config/network.bak
vi /etc/config/network
```

写入以下内容：

```
config interface 'loopback'
	option device 'lo'
	option proto 'static'
	option ipaddr '127.0.0.1'
	option netmask '255.0.0.0'

config globals 'globals'
	option ula_prefix 'fdcf:beab:72ff::/48'

config device
	option name 'br-lan'
	option type 'bridge'
	option ports 'wlan0'

config interface 'lan'
	option device 'br-lan'
	option proto 'static'
	option ipaddr '192.168.1.1'
	option netmask '255.255.255.0'
	option ip6assign '60'

config interface 'wan'
	option device 'wlan1'
	option proto 'dhcp'

config interface 'wan6'
	option device 'wlan1'
	option proto 'dhcpv6'

config interface 'wwan'
	option proto 'dhcp'
```

**重载网络服务：**

```bash
/etc/init.d/network restart && wifi reload
```

### 4.3 获取新分配的局域网 IP

登录主路由后台查看分配给 OpenWrt 网关的新 IP。

| 设备 | IP |
|------|-----|
| Aqara_Hub-1 (floor1_hub) | `192.168.50.234` |
| Aqara_Hub-2 (floor2_hub) | `192.168.50.151` |

---

## 第五部分：刷写 JN5169 芯片为 Zigbee Router 模式

### 5.1 重新 SSH 登录 OpenWrt

```bash
ssh -o HostKeyAlgorithms=+ssh-rsa root@<网关的新局域网IP>
```

若提示密钥冲突，先清理本地 `~/.ssh/known_hosts`。

### 5.2 下载并刷入 Zigbee Router 固件

```bash
wget https://github.com/igorlistopad/Lumi-Router-JN5169/releases/download/2021.3.20/LumiRouter.bin -O /tmp/LumiRouter.bin
jnflash /tmp/LumiRouter.bin
```

幂等钢印存储于 `/etc/jnflash_completed`（持久化路径，重启后不丢失）。

### 5.3 清除 PDM 缓存（防配网失败，必做）

```bash
jntool erase_pdm
```

### 5.4 断电重启（防配网失败，必做）

将网关断电，重新插电启动。

---

## 第六部分：接入智能家居平台 (ZHA / Zigbee2MQTT)

1. 打开 **Zigbee2MQTT** 或 **ZHA** 插件后台，点击 **Permit join**（允许配网）。
2. 将绿米网关断电，重新插电启动。
3. 几秒钟内即可在设备列表中看到新加入的路由器节点（通常识别为 `JN5169`）。
4. 该节点将永久驻留网络，自动为边缘传感器、开关等提供信号中继。

---

## 第七部分：恢复纯净 OpenWrt 出厂默认状态

通过串口（UART）控制台连接：

```bash
sudo picocom -b 115200 /dev/ttyUSB0
```

**彻底清空用户修改（重置 overlay 分区）：**

```bash
firstboot
```

屏幕提示 `Are you sure? [y/N]`，输入 `y` 回车确认。

**重启网关：**

```bash
reboot
```

---

## 第八部分：全面激活并集成原有 Hub 硬件外设 (MQTT)

### 8.1 建立 Home Assistant MQTT 服务器 (Mosquitto Broker)

1. **安装插件：** HA 后台 → **设置 → 插件 → 插件商店**，搜索 `Mosquitto`，安装并开启**开机自启**与**崩溃重启**，点击**启动**。

2. **创建专用用户：** 导航至**设置 → 人员与区域 → 用户**（需先在个人资料中开启"高级模式"），添加用户：

   | 字段 | 值 |
   |------|-----|
   | 用户名 | `mqtt-user` |
   | 密码 | `mqtt-user` |

3. **重启 Mosquitto 插件**，使其同步新用户信息。

4. **启用 MQTT 集成：** **设置 → 设备与服务**，确认或手动添加 **MQTT** 集成，直接点击**提交 → 完成**。

### 8.2 查看 Hub 本地硬件状态

```bash
# 查看 LED 三原色节点
ls /sys/class/leds        # 返回: blue green mmc0:: red

# 查看 ALSA 声卡通道
amixer                    # 返回包含 Master、AlertVol、SnapVol 的混音器参数

# 查看按键输入事件
ls /dev/input/            # 返回: event0
```

### 8.3 安装硬件控制守护进程与 Python 核心依赖

```bash
opkg update
opkg install lumimqtt lumimqttd
opkg install python3-paho-mqtt python3-codecs python3-idna
```

### 8.4 修改原厂服务配置文件

#### 1. 配置 Python 灯光控制端 (`lumimqtt`)

`vi /etc/lumimqtt.json`，写入以下内容（`mqtt_host` 修改为 HA VM 的局域网 IP）：

```json
{
  "mqtt_host": "192.168.50.236",
  "mqtt_port": 1883,
  "mqtt_user": "mqtt-user",
  "mqtt_password": "mqtt-user",
  "topic_root": "lumi/{device_id}",
  "auto_discovery": true,
  "sensor_retain": false,
  "sensor_threshold": 50,
  "sensor_debounce_period": 60,
  "legacy_color_mode": false,
  "light_transition_period": 1.0
}
```

#### 2. 配置 C 语言音频控制端 (`lumimqttd`)

使用 `sed` 复合命令隔离音频端，关闭其网络自发现，防止它覆盖灯光端的彩色配置（`device_id` 中的 MAC 按实际修改）：

```bash
sed -i -e 's/"mqtt_host": "localhost"/"mqtt_host": "192.168.50.236"/g' \
       -e 's/"mqtt_user": ""/"mqtt_user": "mqtt-user"/g' \
       -e 's/"mqtt_user_pw": ""/"mqtt_user_pw": "mqtt-user"/g' \
       -e 's/"auto_discovery": true/"auto_discovery": false/g' \
       -e 's/"device_id": "0x7c49eb93b068"/"device_id": "0x7c49eb93b068_audio"/g' \
       /etc/lumimqttd.json
```

核对修改结果：

```bash
cat /etc/lumimqttd.json | grep -E "mqtt_|auto_discovery|device_id"
```

---

### 8.5 部署独立音频桥接脚本与系统守护进程

音量桥接脚本位于 `roles/gateway_audio_bridge/files/lumi_volume_bridge.py`，由 Ansible 统一分发。

核心配置区域：

```python
MQTT_HOST = "192.168.50.236"
MQTT_PORT = 1883
MQTT_USER = "mqtt-user"
MQTT_PASS = "mqtt-user"
```

MAC 地址通过动态探测获取，接口优先级顺序：`phy0-sta0` → `wlan0` → `wlan0-1` → `eth0` → `br-lan`，兜底值为硬编码 MAC。

Procd 守护服务位于 `roles/gateway_audio_bridge/files/lumi_volume_bridge`，开机自启，崩溃后自动重启。

---

### 8.6 Home Assistant MQTT 核心排毒（至关重要）

历史 Retain 消息会导致 HA 开机持续吃下旧的单色灯配置，造成彩灯变灰（unavailable）。必须手动清除：

1. HA 后台 → **开发者工具 → 服务/动作**，选择 **`MQTT: Publish`**：

   **清理灯光历史残留：**
   - 主题：`homeassistant/light/0x7c49eb93b068/config`
   - 负载：**完全空白**
   - 保留（Retain）：**勾选**
   - 点击**调用服务**

   **清理状态频道冲突：**
   - 主题换为：`lumi/0x7c49eb93b068/status`
   - 其余不变，再次**调用服务**

2. **设置 → 设备与服务 → MQTT**，删除残留的旧设备卡片。

---

### 8.7 启动并全面激活服务

```bash
# 原厂 Python 灯光桥接服务
/etc/init.d/lumimqtt enable
/etc/init.d/lumimqtt restart

# 原厂 C 语言本地音频服务
/etc/init.d/lumimqttd enable
/etc/init.d/lumimqttd restart

# 独立音量桥接服务
/etc/init.d/lumi_volume_bridge enable
/etc/init.d/lumi_volume_bridge restart
```

### 8.8 在 Home Assistant 中的最终效果

刷新 MQTT 集成列表页面，唯一一个干净的设备卡片 `xiaomi_gateway_0x7c49eb93b068` 中包含以下实体：

| 实体类型 | 说明 |
|----------|------|
| 🌟 **夜灯控制** `light.lumi_xxxx` | RGB 原生全彩调色盘与亮度控制 |
| ☀️ **光照传感器** `sensor.illuminance_xxxx` | 物理光敏电阻的实时照度上报 |
| 🔘 **物理按键** `btn0_xxxx` | 捕获单击、双击、长按事件 |
| 🔊 **音量调节** `number.lumi_xxxx_snap_volume` | 硬件提示音量滑块 |
| 🔔 **报警音量** `number.lumi_xxxx_alert_volume` | 硬件报警音量滑块 |

> 💡 通过 MQTT 主题 `lumi/0x7c49eb93b068_audio/play` 可触发网关喇叭播放本地 WAV 文件。

---

## 第九部分：音频功能控制与进阶玩耍指南

### 9.1 硬件双通道混音器原理

网关音频采用级联放大机制，物理音量受 **`Master`（总音量）** 与两个独立硬件增益通道的乘积控制：

| 通道 | 说明 |
|------|------|
| `AlertVol` | 报警音量，高频刺耳，穿透力强（防盗报警、火灾联动） |
| `SnapVol` | 提示音量，柔和短促（门铃声、语音播报提示音） |

### 9.2 本地命令行音频调试

```bash
# 调节报警通道到 80%
amixer sset 'AlertVol' 80%

# 调节提示通道到 50%
amixer sset 'SnapVol' 50%
```

### 9.3 补齐本地音频文件与 MQTT 远程触发播放

**补齐音频文件：**

```bash
mkdir -p /usr/share/sounds
cd /usr/share/sounds
# 使用 wget 从本地服务器或开源仓库下载 .wav 文件
```

**通过 MQTT 触发播放：**

| 操作 | Topic | Payload |
|------|-------|---------|
| 播放音频文件 | `lumi/<MAC>/sound/set` | `/usr/share/sounds/doorbell.wav` |
| 设置报警音量 | `lumi/<MAC>/volumealert/set` | `80` |
| 设置提示音量 | `lumi/<MAC>/volumesnap/set` | `50` |

### 9.4 进阶：变身为 LMS 局域网播放器 & HA 语音播报端

#### 1. 安装 squeezelite

```bash
opkg update
opkg install squeezelite
```

#### 2. 配置并指定 LMS 服务器

`vi /etc/config/squeezelite`，写入以下内容（`server_addr` 按实际修改）：

```
config options 'options'
        option name 'SqueezeWrt'
        option model_name 'SqueezeLite'
        option close_delay '0'
        option priority '0'
        option max_sr '0'
        option device 'default'
        option dsd_over_pcm '0'
        option ircontrol '0'
        option interface ''
        option enabled '1'
        option server_addr '192.168.50.210'
```

#### 3. 激活服务

```bash
/etc/init.d/squeezelite enable
/etc/init.d/squeezelite restart

# 核对运行参数
ps | grep squeezelite
```

#### 4. 在 Home Assistant 中享用原生媒体播放器

通过 HA 的 **Logitech Media Server** 集成，网关会自动生成 `media_player.<网关名称>` 实体，支持在自动化中调用 `tts.speak` 实现语音播报。

---

## 第十部分：批量部署与灾备（Ansible 自动化）

### 10.1 关键配置

**`ansible.cfg`**

```ini
[defaults]
inventory = inventories/production.yml
host_key_checking = False
deprecation_warnings = False
internal_poll_interval = 0.001
stdout_callback = debug

[ssh_connection]
pipelining = True
ssh_args = -o ControlMaster=auto -o ControlPersist=30m -o StrictHostKeyChecking=no
control_path = {directory}/ansible-ssh-%h-%p-%r
```

**`inventories/production.yml`**

```yaml
all:
  vars:
    ansible_ssh_user: root
    ansible_ssh_pass: "uHqZ3P9k"
    ansible_port: 22
  hosts:
    floor1_hub:
      ansible_host: 192.168.50.234
      hub_name: "Lumi Router Floor 1"
      squeezelite_name: "LumiRouter_F1"
      hub_mac: "7c49eb93b068"
    floor2_hub:
      ansible_host: 192.168.50.151
      hub_name: "Lumi Router Floor 2"
      squeezelite_name: "LumiRouter_F2"
      hub_mac: "7c49eb924bd7"
```

**`group_vars/all.yml`**

```yaml
mqtt_host: "192.168.50.236"  # QNAP 虚拟机 HA 的 IP
mqtt_port: 1883
mqtt_user: "mqtt-user"
mqtt_pass: "mqtt-user"
lms_host: "192.168.50.210"   # QNAP 容器 LMS 的 IP
```

### 10.2 自动化可行性矩阵

| 章节内容 | 可行性 | 说明 |
|----------|:------:|------|
| 第一部分：UART 串口 Root 破解 | ❌ | 纯硬件交互，需断电中断 Bootloader |
| 第二部分：原厂系统备份 | ⚠️ | 一次性引导任务，建议手工验证 |
| 第三部分：空中刷入 OpenWrt | ❌ | 刷机过程中 SSH 断开，引发不可控超时 |
| 第四部分：OpenWrt 初始网络桥接 | ⚠️ | 可作为资产前置条件，不建议自动化 |
| 第五部分：JN5169 芯片闪存刷写 | ✅ | `jnflash` + `jntool`，幂等控制 |
| 第八、九部分：环境依赖、配置、脚本、LMS | 🌟 | 自动化核心舞台，天生绝配 |

### 10.3 项目结构

```text
site.yml                       # 总入口 Playbook
status.yml                     # 服务状态检查 Playbook
apply.sh                       # 交互式执行入口脚本
ansible.cfg                    # Ansible 全局配置
inventories/
  production.yml               # 资产清单（物理 IP 等）
group_vars/
  all.yml                      # 全局公用变量（MQTT、LMS IP）
roles/
  ├── gateway_base/            # 基础环境：公共依赖包
  ├── gateway_zigbee/          # 固件刷写：JN5169 Zigbee Router
  ├── gateway_lumi_mqtt/       # 原厂组件：lumimqtt / lumimqttd
  ├── gateway_squeezelite/     # 串流播放：LMS 客户端
  ├── gateway_audio_bridge/    # 音频桥接：音量控制 Python 守护服务
  └── gateway_wifi_watchdog/   # WAN 看门狗：断线自动启用 AP 救援热点
```

### 10.4 执行方式

```bash
# 完整部署
./apply.sh  # 选择 1) Deploy

# 检查服务状态
./apply.sh  # 选择 2) Status
```

### 10.5 WAN 看门狗（gateway_wifi_watchdog）

当 WAN 侧 `phy0-sta0` 接口断线超过 **3 次检测（30 秒）** 后，自动启用 `radio1` AP 救援热点（SSID: `OpenWrt`），供本地 SSH 接入排查。WAN 恢复稳定后自动关闭 AP。

检测间隔：`10` 秒；触发阈值：`3` 次连续失败/成功。

---

## 附录：物理按键复位速查

> 按键期间灯不亮，**松手时**灯才亮。

| 长按时长 | 灯光表现 | 效果 |
|----------|----------|------|
| **10 秒** | 黄灯闪烁 3 次 | 重置无线网络配置，重新释放 OpenWrt AP 救援热点 |
| **20 秒** | 红灯闪烁 3 次 | 彻底擦除 overlay 分区，恢复刷机后最干净初始状态 |
