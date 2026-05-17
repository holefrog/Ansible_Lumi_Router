# ZHWG11LM (Aqara Hub v1) 全套玩机终极指南：从获取 Root 到全面接入 Home Assistant

本指南适用于将绿米网关 **ZHWG11LM (Aqara Hub)** 彻底解锁，空中刷入 OpenWrt 系统，将板载 JN5169 芯片配置为通用的 Zigbee Router（中继器），并最终通过 MQTT 将网关原厂硬件（RGB夜灯、物理按键、光照传感器、音量调音台与喇叭）全面桥接融入 Home Assistant 智能家居生态。

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

---

## 第一部分：获得 Root 权限并创建 SSH 服务器

* **参考文档:** [https://openlumi.github.io/gain_root.html]
* **默认参考 Root 凭据:** `uHqZ3P9k`

### 核心操作步骤

#### 1. 中断启动引导 (Stop booting)
1. 使用 **115200** 波特率连接网关的硬件串口（UART）。
2. 在设备上电后的瞬间，立即在串口终端（UART Terminal）中频繁按下**任意键**以阻止系统继续引导。
3. *注意：如果终端没有成功停在 `=>` 提示符处，说明未能成功中断。请拔掉网关电源重新插上并重复上述操作。*

#### 2. 获取临时 Root 权限 (Get root)
在引导提示符 `=>` 后面输入以下命令并回车，以单用户读写模式挂载并启动系统内核：
```bash
setenv bootargs "${bootargs} single rw init=/bin/bash" && boot
```

#### 3. 修改 Root 密码 (Change root passwd)
进入系统后输入修改密码命令：
```bash
passwd
```
连续按下 **3 次回车键**，此时 root 用户的密码将被成功设置为空。

#### 4. 启用 SSH 服务 (Enable ssh)
要在网关上永久启用 SSH 服务器，需要在 `/etc/rc.local` 文件的末尾、且在 `/home/root/fac/fac_test` 行之前添加启动脚本。

1. 使用 vi 编辑器打开文件：
```bash
vi /etc/rc.local
```
2. 在 **`/home/root/fac/fac_test`** 行的**前面**精准添加以下内容：
```text
/etc/init.d/dropbear start &
```

#### 5. 保存更改 (Save)
执行同步命令以确保所有内存修改安全写入闪存：
```bash
sync
```

#### 6. 重启设备 (Restart)
将网关断电，然后重新上电正常启动。

---

### 常见错误与解决办法 (Troubleshooting)

如果你在尝试连接 SSH 时接收到如下错误提示：
```text
Starting Dropbear SSH server: Pseudo-terminal will not be allocated because stdin is not a terminal.
ssh: connect to host rsa port 22: Connection refused
```

* **错误原因：** 这意味着你网关当前自带的原厂 dropbear 固件在编译时没有包含 ssh-server（服务器端）功能，它只能作为客户端使用。
* **解决方案：** 请重新进入临时 root环境，按照以下步骤将其替换为一个功能完整的全功能 SSH 服务器。

#### 步骤一：登录正常系统的控制台
1. 开机滚屏结束后，根据官方说明系统会进入测试控制台模式。
2. 在键盘上输入 `exit_factory` 并回车，退出测试模式。
3. 随后会出现 `login:` 提示符。输入 `root`，并输入你之前设定的密码（如果之前置空了则直接回车）。此时你便进入了完整的 Linux 生产环境中。

#### 步骤二：建立功能完整的 SSH Server
1. **强行向 HUB 注入 Google 公共 DNS 服务器：**
   ```bash
   echo "nameserver 8.8.8.8" > /etc/resolv.conf
   ```
2. **测试 HUB 此时能否成功解析并 Ping 通外网（按 Ctrl+C 可以退出）：**
   ```bash
   ping -c 3 raw.githubusercontent.com
   ```
3. **将 HUB 原厂自带的那个被阉割的旧文件改名备份：**
   ```bash
   mv /usr/sbin/dropbearmulti /usr/sbin/dropbearmulti.backup
   ```
4. **通过 openssl 建立加密连接，把原始响应数据下载到临时文件中：**
   ```bash
   echo -e "GET /openlumi/openlumi.github.io/master/files/dropbearmulti HTTP/1.0\nHost: raw.githubusercontent.com\n" > /tmp/request.txt
   openssl s_client -quiet -connect raw.githubusercontent.com:443 -servername raw.githubusercontent.com < /tmp/request.txt > /tmp/raw_response.txt
   ```
   *注意：请忽略以下证书验证报错，这不影响文件正常下载：*
   ```text
   depth=1 C = US, O = Let's Encrypt, CN = R12
   verify error:num=20:unable to get local issuer certificate
   ```
5. **检查下载的文件大小，只要结果不为 0 即代表正常：**
   ```bash
   ls -l /tmp/raw_response.txt
   ```
6. **利用 sed 过滤掉文件顶部的 HTTP 文本头，把干净的二进制可执行文件提取到目标路径：**
   ```bash
   sed '1,/^\r$/d' /tmp/raw_response.txt > /usr/sbin/dropbearmulti
   ```
7. **赋予文件可执行权限：**
   ```bash
   chmod +x /usr/sbin/dropbearmulti
   ```
8. **重新建立软链接 (Link)：**
   ```bash
   ln -sf /usr/sbin/dropbearmulti /usr/sbin/dropbear
   ```
9. **手动启动 SSH 服务 (Start SSH)：**
   ```bash
   /etc/init.d/dropbear start
   ```
10. **在客户端电脑上测试连接 (Connect)：**
    ```bash
    ssh -o HostKeyAlgorithms=+ssh-rsa root@192.168.50.234
    ```

---

## 第二部分：备份原厂固件（原厂 SSH 环境）

由于每个网关的官方证书、密钥、MAC 地址都是独一无二的，**严禁跳过备份步骤**。一旦丢失，设备将永久无法连接绿米云端或恢复原厂。

### 2.1 轻量密钥备份（备份至云端文本流）
1. 使用 SSH 工具登录到网关官方系统。
2. 执行以下命令，自动遍历 `/lumi/conf/` 目录下的所有出厂配置文件，并通过管道上传到公共文本分享服务：
   ```bash
   cd /lumi/conf/
   for fn in *; do printf "=== Start $fn ===\n"; cat "$fn"; printf "=== End $fn ===\n"; done | nc termbin.com 9999
   ```
3. **关键：** 命令执行后，终端会输出一个类似 `http://termbin.com/xxxx` 的 URL 链接。请务必 in 浏览器中打开该链接，将网页中显示的文本完整复制并保存到你本地电脑的 txt 文件中。

### 2.2 完整系统备份（打包根目录）
1. 在网关 SSH 终端中执行以下命令，将除临时目录外的所有系统文件打包压缩：
   ```bash
   tar -cvpzf /tmp/lumi_stock.tar.gz -C / . --exclude='./tmp/*' --exclude='./proc/*' --exclude='./sys/*'
   ```
   *注意：打包过程可能需要 5 分钟，请耐心等待命令执行完毕回到提示符。*
2. **将备份下载到本地电脑：** 打开你本地电脑的终端（例如你的 ThinkPad），执行以下 `scp` 命令将网关上的备份拉取到本地：
   ```bash
   scp -O -o HostKeyAlgorithms=+ssh-rsa root@192.168.50.234:/tmp/lumi_stock.tar.gz .
   ```

---

## 第三部分：空中刷入 OpenWrt 系统 (OTA)

此步骤将利用官方系统的漏洞和残留工具链，直接从 OpenLumi 官方仓库下载并替换系统内核与引导。

### 3.1 执行一键刷机脚本
1. 确保网关目前已正常联网。
2. 在网关的原厂 SSH 终端中复制并执行以下复合命令：
   ```bash
   echo -e "GET /openlumi/owrt-installer/main/install.sh HTTP/1.0\nHost: raw.githubusercontent.com\n" | openssl s_client -quiet -connect raw.githubusercontent.com:443 -servername raw.githubusercontent.com 2>/dev/null | sed '1,/^\r$/d' | bash
   ```
3. **预期现象：** 脚本开始运行后，会强制终止网关的所有 lumi 官方业务进程。此时，你的 **SSH 连接会立即断开并提示超时**，这是完全正常的。
4. **耐心等待：** 网关此时正在后台擦除分区并写入 OpenWrt。请静置设备 **3 至 5 分钟**，期间绝对不能断电。

---

## 第四部分：配置 OpenWrt 网络环境

刷写成功后，网关会彻底蜕变为一台运行 OpenWrt 系统的微型路由器，并默认发射无线信号。

### 4.1 连接网关初始 Wi-Fi
1. 用电脑或手机搜索无线网络，连接名为 **OpenWrt** 的无密码开放 Wi-Fi。
2. 打开浏览器，访问网关默认管理地址：`http://192.168.1.1` 进入 LuCI 界面。
3. 默认用户名为 `root`，**密码为空**（不要输入任何密码），直接点击 **Login** 登录。
4. **修改 root 密码：** 建议立即在系统管理中将密码修改为 `*8^6#3Ab` 并保存。

### 4.2 桥接至家里主路由的 Wi-Fi 网络（双方法选择）

> ⚠️ **排坑警告**：由于 ZHWG11LM 固件的无线芯片驱动限制，采用网页端（方法一）操作极易导致无线芯片由于在 AP/STA 模式切换间瞬时死锁。**强烈推荐直接使用方法二通过命令行修改“两个文件”，稳定可靠。**

#### 【方法一：通过 LuCI 网页操作（极易冲突失败/不推荐）】
1. 在 LuCI 菜单栏中，依次点击 **Network** -> **Wireless**（网络 -> 无线）。
2. 在无线接口列表（通常显示为 `Generic MAC80211 802.11bgn` (**radio0**)）中，点击 **Scan**（扫描）按钮。
3. 在弹出的周围 Wi-Fi 列表中，找到你家主路由的 2.4GHz Wi-Fi 名称，点击其右侧的 **Join Network**（加入网络）。
4. 在随后的配置页面中：
   * 勾选 **Replace wireless configuration**（替换无线配置，这会覆盖原本发射的 OpenWrt 热点）。
   * 在 **WPA passphrase**（无线密码）栏中，准确输入你家 Wi-Fi 的密码。
   * 点击右下角的 **Submit**（提交）。
5. 页面刷新后，直接滚动到最下方，点击 **Save & Apply**（保存并应用）。
6. **关键一步**：再次回到 **Network** -> **Wireless** 页面，在 Client (radio 0) 下面会显示：**UNSAVED CHANGES: 17**。点击进去进行最终的 Save。此时 HUB 就会重启并作为客户端连接到主路由器。
7. （注：如果原先发射 `OpenWrt` 信号的那个 SSID 接口还在，请点击它旁边的 **Disable** 予以禁用，避免无线冲突）。

#### 【方法二：手动修改无线配置文件（纯命令行/百分之百成功/强烈推荐 🌟）】
无需通过网页点选，在网关本地的串口或通过连接初始 OpenWrt 热点后 SSH 登录，直接手动修改底层的无线配置文件，强行固定为 STA 纯客户端接入。

1. **修改配置文件 `/etc/config/wireless`：**
   执行命令 `vi /etc/config/wireless`，将其内部的无线接口彻底重写为如下纯 Station 结构：
   ```text
   config wifi-device 'radio0'
       option type 'mac80211'
       option channel 'auto'
       option hwmode '11g'

   config wifi-iface 'default_radio0'
       option device 'radio0'
       option network 'lan'
       option mode 'sta'
       option ssid '你家主路由的2.4G无线名称'
       option encryption 'psk2'
       option key '你家无线的密码'
   ```
2. **重载网络服务使其生效：**
   在终端执行以下命令重新初始化网络堆栈与无线配置：
   ```bash
   /etc/init.d/network restart
   wifi reload
   ```

### 4.3 获取新分配的局域网 IP
此时，网关将断开与你电脑的直连。请登录你家主路由的后台，查看到网关被分配的新局域网 IP（名称显示为 OpenWrt）。
* *已知分配设备 IP 参考：*
  * **Aqara_Hub-1**: `192.168.50.234`
  * **Aqara_Hub-2**: `192.168.50.151`

---

## 第五部分：刷写 JN5169 芯片为 Zigbee Router 模式

网关的 Zigbee 功能是由板载的 NXP JN5169 芯片提供的。OpenWrt 系统中已经内置了刷写该芯片的工具。

### 5.1 SSH 重新登录 OpenWrt
打开本地电脑终端，使用刚才在主路由里查到的**新 IP** 重新登录网关：
```bash
ssh -o HostKeyAlgorithms=+ssh-rsa root@<网关的新局域网IP>
```
*提示：如果提示密钥冲突，请先在本地电脑清理 `~/.ssh/known_hosts`。*

### 5.2 下载并刷入 Zigbee Router 固件
1. 在 OpenWrt 终端中，下载由社区针对该网关优化的开源 Zigbee Router 固件（由 igo-r 维护）：
   ```bash
   wget [https://github.com/igorlistopad/Lumi-Router-JN5169/releases/download/2021.3.20/LumiRouter.bin](https://github.com/igorlistopad/Lumi-Router-JN5169/releases/download/2021.3.20/LumiRouter.bin) -O /tmp/LumiRouter.bin
   ```
2. 使用系统自带的 `jnflash` 工具，将固件刷入串行的 Zigbee 芯片中：
   ```bash
   jnflash /tmp/LumiRouter.bin
   ```

### 5.3 强力清除 PDM 缓存（防配网失败必做）
旧的原厂 Zigbee 网络密钥和邻居表会缓存在芯片的 PDM 区域，如果不清除，会导致其无法加入新的 Zigbee 协调器。执行以下命令强制清空：
```bash
jntool erase_pdm
```

### 5.4 必须断电（防配网失败必做）
将绿米网关断电，重新插电启动。

---

## 第六 部分：接入智能家居平台 (ZHA / Zigbee2MQTT)
至此，硬件层面的刷写已全部完成。该网关现在是一个完全标准的通用 Zigbee 路由中继设备。
1. 打开你的 **Zigbee2MQTT** 或 Home Assistant 的 **ZHA** 插件后台。
2. 点击 **Permit join**（允许添加新设备 / 开启全局配网）。
3. 将绿米网关断电，重新插电启动。
4. 网关在没有网络连接记录时会自动进入配网模式。几秒钟内，你就会在设备列表中看到一个新加入的路由器节点（通常识别为 `JN5169`）。
5. 它将永久驻留在你的网络中，自动为你边缘的温湿度传感器、开关等设备提供强劲的信号中继。

---

## 第七部分：恢复纯净 OpenWrt 出厂默认状态

如果你在配置网络或无线时失误导致断联，可以直接通过 **串口（UART）控制台** 执行以下命令，将系统恢复到刚刷完机、最干净的出厂默认状态（清空所有配置、恢复默认的 OpenWrt 热点和 `192.168.1.1` 管理 IP）：

1. **清除所有用户修改的配置（重置 overlay 分区）：**
   ```bash
   firstboot
   ```
   屏幕上会提示：`This will erase all settings and remove any installed packages. Are you sure? [y/N]`。请在键盘上输入 `y` 并回车确认。
2. **重启网关：**
   ```bash
   reboot
   ```

---

## 第八部分：全面激活并集成原有 Hub 硬件外设 (MQTT)

由于 Zigbee 路由固件只接管了 JN5169 芯片，网关外壳上的 **RGB夜灯、物理按键、光照传感器、音量调音台与喇叭** 均由主控 OpenWrt 系统直接驱动。本章将采用“架构级解耦”的黑客优雅解法，彻底终结原厂两端冲突的历史包袱，在 Home Assistant 中实现单一设备的完美全功能合体。

### 8.1 建立 Home Assistant MQTT 服务器 (Mosquitto Broker)

如果你尚未建立 MQTT 服务器，请先在 HA 中进行以下部署：

1. **安装 Mosquitto Broker 插件：**
   * 打开 HA 网页后台，依次点击 **设置 (Settings) -> 插件 (Add-ons)**。
   * 点击右下角的 **“插件商店”** 按钮。
   * 搜索 `Mosquitto`，找到 **Mosquitto broker** 并点击安装。
   * 安装完成后，打开 **“开机自启”** 和 **“崩溃重启”** 开关，点击 **启动 (Start)**。
2. **为 MQTT 创建专用的 HA 用户：**
   * 导航至 **设置 -> 人员与区域 -> 用户 (Users)** 标签页（若没看到“用户”，请先在 HA 左下角个人资料里打开“高级模式”）。
   * 点击 **“添加用户”**。创建账号：用户名 `mqtt-user`，密码 `mqtt-user`。点击创建。
3. **重启 Mosquitto 插件：**
   * **关键防坑：** 务必回到 Mosquitto 插件页面，点击 **重启 (Restart)**，使其强制同步刚刚创建的新用户信息。
4. **在 Home Assistant 中启用 MQTT 集成：**
   * 导航至 **设置 -> 设备与服务**，此时顶部通常会自动提示“发现新设备：MQTT”，点击 **配置**。
   * 如果没有自动弹出，点击“添加集成”手动搜索 **MQTT**。
   * 集成会探测到 Add-on 插件，界面会弹出一键确认提示（不需要手动填任何 IP 与账号），直接点击 **提交 (Submit)** -> **完成 (Finish)**。

### 8.2 查看 Hub 本地硬件状态
在网关的 OpenWrt 终端中，你可以通过以下标准指令确认硬件节点的健全：
```bash
# 查看LED三原色节点
ls /sys/class/leds        # 返回: blue green mmc0:: red
# 查看ALSA声卡通道
amixer                    # 返回包含 'Master', 'AlertVol', 'SnapVol' 的混音器参数
# 查看按键输入事件
ls /dev/input/            # 返回: event0
```

### 8.3 在线安装硬件控制守护进程与 Python 核心依赖
确保网关已连接外网，在网关终端执行以下命令。除了灯光包与音频包外，**必须同步补齐 Python 的核心标准编码与域名解析依赖库**，否则音频桥接脚本会因缺少网络轮子引发 `unknown encoding: idna` 错误而陷入后台无限闪退：
```bash
# 1. 更新原厂固件包索引
opkg update

# 2. 安装原厂灯光/按键包与音频控制包
opkg install lumimqtt lumimqttd

# 3. 补齐 Python3 核心标准编码、通讯及基础设施依赖包（关键防坑）
opkg install python3-paho-mqtt python3-codecs python3-idna
```

### 8.4 修改原厂服务配置文件（斩断污染源）

#### 1. 配置 Python 灯光控制端 (`lumimqtt`)
执行 `vi /etc/lumimqtt.json`，将内容彻底清空并替换为以下标准扁平化结构。
*注意：`mqtt_host` 必须精确修改为你 QNAP 虚拟机（HA VM）的独立局域网 IP（例如 `192.168.50.236`），并将 `legacy_color_mode` 设为 `false` 以适配新版 HA 的颜色选择器：*
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
为了防止 C 语言端过时的单色灯自动发现载荷在网络上投毒、覆盖掉 Python 端好不容易生成的全彩调色盘，我们使用以下经过严密调试的 `sed` 复合命令。**强行关闭其网络自发现，并将它的 `device_id` 加上隔离外衣（改为 `_audio` 后缀）**，彻底剥离其网络污染能力，使其退化为纯粹的本地 WAV 播放器：
```bash
sed -i -e 's/"mqtt_host": "localhost"/"mqtt_host": "192.168.50.236"/g' \
       -e 's/"mqtt_user": ""/"mqtt_user": "mqtt-user"/g' \
       -e 's/"mqtt_user_pw": ""/"mqtt_user_pw": "mqtt-user"/g' \
       -e 's/"auto_discovery": true/"auto_discovery": false/g' \
       -e 's/"device_id": "0x7c49eb93b068"/"device_id": "0x7c49eb93b068_audio"/g' \
       /etc/lumimqttd.json
```
替换完成后，可使用以下命令人工核对修改：
```bash
cat /etc/lumimqttd.json | grep -E "mqtt_|auto_discovery|device_id"
```

---

### 8.5 部署独立音频桥接脚本与系统守护进程

既然 C 语言端在网络上成了“哑巴”，我们编写一个完全独立解耦的轻量级 Python 脚本来扮演“音量桥接器”角色。它会拿着和 Python 灯光端 100% 像素级对齐的真实原厂身份钢印（`xiaomi_gateway_0x...`），强行将声卡音量实体归流合并。

#### 1. 创建核心桥接脚本
在网关创建脚本文件：`vi /usr/bin/lumi_volume_bridge.py`
赋予脚本特权：
```bash
chmod +x /usr/bin/lumi_volume_bridge.py
```

#### 2. 创建 Procd 开机守护服务
创建初始化运行脚本：`vi /etc/init.d/lumi_volume_bridge`
赋予服务特权：
```bash
chmod +x /etc/init.d/lumi_volume_bridge
```

---

### 8.6 Home Assistant MQTT 核心“排毒”大扫除（至关重要）

由于在早前测试阶段，MQTT 服务器（Mosquitto）内部已经永久固化并保留（Retain）了单色灯的错误宣告以及错误的离线状态遗嘱，**如果不彻底洗净，无论如何重启网关，HA一开机还是会吃下历史毒药配置导致彩灯一碰就死锁变灰（unavailable）**。请严格执行以下手动大排毒：

1. 打开 HA 电脑浏览器，依次进入 **开发者工具 (Developer Tools) -> 服务/动作 (Actions)** 选项卡。
2. 搜索并选择 **`MQTT: Publish`** 服务，切换到 UI 模式：
   * **清理灯光历史残留：**
     * **主题 (Topic)** 精准填入：`homeassistant/light/0x7c49eb93b068/config`
     * **负载 (Payload)**：**保持绝对完全空白，一个字都不要填！**
     * **保留 (Retain)** 开关：**必须勾选勾亮 / 设为 True**。
     * 点击底部的 **调用服务 (Call Action)**。
   * **清理状态频道冲突：**
     * 保持其余选项完全不变，仅将 **主题 (Topic)** 换成：`lumi/0x7c49eb93b068/status`
     * 再次点击 **调用服务 (Call Action)**。
3. 前往 **HA -> 设置 -> 设备与服务 -> MQTT**，把当前残留的那个不断报错的网关旧设备卡片，直接点击 **删除 (Delete)** 彻底清理出户。

---

### 8.7 启动并全面激活服务

在网关终端顺次执行以下命令，全面唤醒三维一体解耦架构服务，并全部设为开机自启：
```bash
# 1. 激活并启动原厂 Python 灯光桥接服务
/etc/init.d/lumimqtt enable
/etc/init.d/lumimqtt restart

# 2. 激活并启动原厂 C 语言本地音频服务
/etc/init.d/lumimqttd enable
/etc/init.d/lumimqttd restart

# 3. 激活并启动我们编写的独立音量桥接服务
/etc/init.d/lumi_volume_bridge enable
/etc/init.d/lumi_volume_bridge restart
```

---

### 8.8 在 Home Assistant 中享用完美单一设备

现在，刷新你的 **Home Assistant MQTT 集成列表页面**。你会惊奇地发现，原本混乱的多个报错设备已经不复存在，取而代之的是**唯一一个干净完美的物理硬件设备卡片 `xiaomi_gateway_0x7c49eb93b068`**。

点进卡片，里面的控制实体实现了大满贯融合：
* 🌟 **夜灯控制 (Light)：** `light.lumi_xxxx`（100% 健全且绝不报错的 RGB 原生全彩调色盘与亮度控制条）。
* ☀️ **光照传感器 (Sensors)：** `sensor.illuminance_xxxx`（网关正面物理光敏电阻的实时照度上报）。
* 🔘 **物理按键 (Buttons)：** `btn0_xxxx`（可在 HA 自动化中完美捕获网关顶部物理按键的单击、双击、长按事件）。
* 🔊 **音量调节 (Numbers)：** 成功合并进来的 **`Snap Volume`**（带标准高音量喇叭图标）与 **`Alert Volume`**（带标准警报铃铛图标）两个硬件音量滑块。在 HA 里任意拉动，即可实时通过底层 ALSA 改变网关真实喇叭放声时的音量大小！

> 💡 **高级联动贴士**：由于 C 语言音频端被我们优雅隔离到了 `_audio` 后缀下，后续如果想在 HA 的自动化脚本中调用网关的扬声器播放特定的本地 WAV 铃声文件，只需要将 MQTT 发送的目标控制主题设置为 `lumi/0x7c49eb93b068_audio/play` 即可，做到了前端极致高内聚，后端底层低耦合。



## 第九部分：音频功能控制与进阶玩耍指南

通过安装并配置 `lumimqttd`，网关内置的 ALSA 声卡和硬件功放已被完全激活。这一部分将详细介绍如何在本地调试音量、如何通过 MQTT 远程控制网关播放声音，以及如何将其改造为局域网内的 TTS 语音播报音箱。

### 9.1 硬件双通道混音器（AlertVol / SnapVol）原理解析

网关的音频输出采用了级联放大机制，物理音量受制于 **`Master`（总音量）** 结合两个独立硬件增益通道的乘积：
* **`AlertVol`（报警音量）**：专门对应高频、刺耳、穿透力强的音频输出电路（如防盗报警、火灾联动）。
* **`SnapVol`（提示音量）**：专门对应柔和、短促的日常音频输出电路（如门铃叮咚声、语音播报提示音）。

> 💡 **核心操作**：如果 Home Assistant 的 MQTT 集成已成功自动发现该设备，你会在设备面板的 **Controls (控制)** 区域看到两个标准的 `Number` 滑块实体：`number.lumi_xxxx_alert_volume` 和 `number.lumi_xxxx_snap_volume`。你可以直接在 HA 仪表盘中拉动它们，或编写自动化在夜间动态调低 `SnapVol` 以免门铃声惊扰家人。

---

### 9.2 本地命令行音频调试（SSH / 串口）

在网关终端中，你可以直接使用 Linux 标准的 `amixer` 工具对这两路硬件通道进行百分比或绝对数值的独立控制与测试：

* **调节硬件报警音量到 80%**：
  ```bash
  amixer sset 'AlertVol' 80%
  ```
* **调节硬件提示音量到 50%**：
  ```bash
  amixer sset 'SnapVol' 50%
  ```

---

### 9.3 找回原厂铃声与 MQTT 远程触发播放

刷入纯净版 OpenWrt 后，系统内默认不包含任何音频文件。需要手动补齐音频源，并通过 MQTT 消息触发播放。

#### 1. 补齐本地音频文件
进入网关终端，在 `/usr/share/` 下创建存放声音的目录，并下载开源社区提取出的原厂经典音频包（通常包含 `0.wav` 到 `20.wav` 等门铃和警报声）：
```bash
mkdir -p /usr/share/sounds
cd /usr/share/sounds
# 可使用 wget 从你的本地服务器或开源仓库下载对应的 .wav 文件到此目录下
```

#### 2. 通过 MQTT 触发网关发声
`lumimqttd` 成功运行后会持续监听局域网中的控制主题。你可以在 Home Assistant 的自动化或脚本中直接调用 `MQTT: Publish` 动作发送控制指令：

* **触发播放指定的音频文件**：
  * **Topic**: `lumi/<你的网关MAC地址>/sound/set` （例如 `lumi/7c49eb93b068/sound/set`）
  * **Payload** (文件绝对路径): `/usr/share/sounds/doorbell.wav`
* **设置报警通道音量 (0-100)**：
  * **Topic**: `lumi/<你的网关MAC地址>/volumealert/set`
  * **Payload**: `80`
* **设置提示通道音量 (0-100)**：
  * **Topic**: `lumi/<你的网关MAC地址>/volumesnap/set`
  * **Payload**: `50`

---

### 9.4 进阶高阶玩法：变身为 LMS 局域网播放器 & HA 语音播报端

既然网关的 ALSA 声卡驱动（`Master`/`AlertVol`/`SnapVol`）已经百分之百健全，你可以更进一步，将其打造为一个可以被 Home Assistant 直接接管并实现 **TTS（文本转语音）** 播报的独立局域网无线音箱。

通过在 OpenWrt 内部部署极其轻量化的 **`squeezelite`** 客户端，网关能够无缝挂靠到局域网中现有的 **LMS (Logitech Media Server)** 服务器上。

#### 1. 在网关上安装并启用 squeezelite
在网关终端执行安装包命令：
```bash
opkg update
opkg install squeezelite
```

#### 2. 配置并指定 LMS 服务器
编辑网关的 `squeezelite` 配置文件：
```bash
vi /etc/config/squeezelite
```
配置其启动参数，确保音频输出设备指定为本地 ALSA 默认设备（`default`），并且在参数中填入你局域网中 LMS 服务器的实际 IP 地址。

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

激活服务与活体状态核验

完成配置后，请在终端顺次执行以下命令，唤醒系统内置的 procd 守护进程并检查连通性：
Bash

# 1. 设置 Squeezelite 客户端为开机自启动，并重载服务
/etc/init.d/squeezelite enable
/etc/init.d/squeezelite restart

# 2. 检查进程树，核对底层最终拼接生成的运行参数
ps | grep squeezelite


#### 3. 在 Home Assistant 中享用原生媒体播放器
启动网关的 `squeezelite` 服务后，它会立刻作为标准的播放端登记在你的 LMS 中。
通过 Home Assistant 的 **Logitech Media Server** 官方集成，HA 内部会瞬间为你生成一个极其标准的 `media_player.<网关名称>` 媒体播放器实体。

至此，你不仅可以在网关上随心所欲播放局域网内的网络电台或音乐，更能在自动化中直接调用 `tts.speak` 服务（例如：“洗衣机工作已完成”、“大门已被打开”），让网关外壳的喇叭成为你智能家居最完美的真语音播报终端！
