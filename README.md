
元宝

# 🎮 手柄震动映射 · Rumble Shock

> [中文](#中文) ｜ [English](#english)

**手柄一震动，郊狼就放电。** 监听 XInput 震动信号，实时联动 DGHub，驱动 DG-Lab 设备输出沉浸式反馈。
*Controller rumbles → Coyote shocks. Hook XInput vibration calls and trigger DG-Lab devices through DGHub.*

[![Version](https://img.shields.io/badge/version-1.6.0-blue)](https://github.com) [![DGHub](https://img.shields.io/badge/DGHub-v1.8.2%2B-green)](http://www.dghub.top/)

---

## 📑 目录 · Table of Contents

<details open>
<summary>🇨🇳 中文 / Chinese</summary>

- [插件简介](#-插件简介)
- [快速开始](#-快速开始)
- [基本配置](#️-基本配置)
- [兼容说明](#-兼容说明)
- [前置软件](#️-前置软件)
- [主要功能](#-主要功能)
- [更新日志](#-更新日志)
- [注意事项](#️-注意事项)
- [源码说明](#-源码说明)
- [免责声明](#️-免责声明)

</details>

<details>
<summary>🇬🇧 English</summary>

- [Introduction](#-introduction)
- [Quick Start](#-quick-start)
- [Basic Setup](#️-basic-setup)
- [Compatibility](#-compatibility)
- [Requirements](#️-requirements)
- [Features](#-features)
- [Changelog](#-changelog)
- [Notes](#️-notes)
- [Source Code](#-source-code)
- [Disclaimer](#️-disclaimer)

</details>

> 💡 **提示**：点击上方 `summary` 箭头可一键收起/展开对应语言目录；下方正文中 **[🇨🇳 中文]** 与 **[🇬🇧 EN]** 标签可通过「折叠区块」自由切换阅读。

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## 📖 插件简介

<details open>
<summary><b>[🇨🇳 中文]</b> 点击展开/收起 · Click to toggle</summary>

本插件会挂钩游戏进程中的 `XInputSetState`，实时获取左右马达震动强度，并按你配置的规则映射为电击强度与波形，通过 DGHub 发送给已连接的 DG-Lab 设备。

**一句话效果：** 游戏手柄震动 → 插件检测 → DGHub 触发 → 郊狼放电

</details>

<details>
<summary><b>[🇬🇧 EN]</b> Click to expand</summary>

The plugin intercepts `XInputSetState` in the target game process, reads left/right motor intensity, converts it according to your settings, and sends trigger commands to DGHub.

**One-line summary:** Game controller rumble → Plugin detects → DGHub triggers → Device output

</details>

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## 🚀 快速开始

<details open>
<summary><b>[🇨🇳 中文]</b></summary>

**1. 下载与解压**
本项目采用分卷压缩上传，请下载以下文件并放在同一文件夹：

- `手柄震动联动.7z.001`
- `手柄震动联动.7z.002`
- `手柄震动联动.7z.003`

使用 7-Zip、Bandizip、WinRAR 等解压即可。若解压遇到问题，可使用附带的 `手柄震动联动.exe` 辅助解压。

**2. 导入插件**
解压后找到 `main.zip`（插件本体），打开 **DGHub → 插件中心 → 外部插件 → 导入该 zip**。

</details>

<details>
<summary><b>[🇬🇧 EN]</b></summary>

**1. Download & Extract**
Please download all parts and put them in the same folder, then extract with 7-Zip, Bandizip, WinRAR, or similar. If extraction fails, use the included helper exe.

- `手柄震动联动.7z.001`
- `手柄震动联动.7z.002`
- `手柄震动联动.7z.003`

**2. Import Plugin**
Locate `main.zip`, open **DGHub → Plugin Center → External Plugins → Import the zip**.

</details>

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## ⚙️ 基本配置

<details open>
<summary><b>[🇨🇳 中文]</b></summary>

1. 在插件配置页填写要监听的**游戏进程名**
2. 确认游戏使用 **XInput** 手柄输入
3. **禁用 Steam 输入（重要）**
4. 选择输出通道、强度模式、波形预设等参数

> ⚠️ 配置如遇问题，请优先查看 DGHub 运行日志，确认无报错后再重启插件。**插件运行时无法修改配置，请先停止再调整。**

</details>

<details>
<summary><b>[🇬🇧 EN]</b></summary>

1. Enter the target **game process name** in settings
2. Make sure the game uses **XInput**
3. **Disable Steam Input (important)**
4. Configure channel, strength mode, preset, etc.

> ⚠️ Check the DGHub runtime log first, then restart. Settings cannot be changed while running — stop it before editing.

</details>

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## 🧩 兼容说明

<details open>
<summary><b>[🇨🇳 中文]</b></summary>

理论上支持所有通过 XInput 控制手柄震动的游戏，实际兼容性因游戏实现而异，需自行验证。**必须使用支持 XInput 的手柄，并关闭 Steam Input。**

**已验证兼容游戏**

| 游戏 | 进程名 | 适配程度 |   
| :--- | :--- | :--- |   
| 星际拓荒 (Outer Wilds) | `OuterWilds.exe` | 完美 |   
| 死亡搁浅 导演剪辑版 | `ds.exe` | 一般：DGHUB后台运行时插件可能被杀后台 |   
| 怪物猎人：崛起 |`MonsterHunterRise.exe` | 完美 |  

**无效果排查清单**
- [ ] 进程名是否填写正确
- [ ] 是否已禁用 Steam 输入
- [ ] 手柄是否走 XInput

</details>

<details>
<summary><b>[🇬🇧 EN]</b></summary>

In theory, any game that drives rumble via XInput is supported. Real-world compatibility varies. **Use an XInput-compatible controller and disable Steam Input.**

**Verified Games**

| Game | Process | effect |  
| :--- | :--- | :---|  
| Outer Wilds | `OuterWilds.exe` | prefect |  
| Death Stranding Director's Cut | `ds.exe` | normal |   
| Monster Hunter Rise | `MonsterHunterRise.exe`  | prefect |   

**Troubleshooting**
- [ ] Process name is correct
- [ ] Steam Input is disabled
- [ ] Controller is using XInput

</details>

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## 🛠️ 前置软件

| 软件 | 说明 | 链接 |
| :--- | :--- | :--- |
| **DGHub** | 插件运行与设备控制中枢 | [下载](http://www.dghub.top/) |
| **DG-Lab** | 官方设备与生态 | [官网](https://dungeon-lab.cn/) |

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## ✨ 主要功能

<details open>
<summary><b>[🇨🇳 中文]</b></summary>

- 实时监听 XInput 手柄震动
- 支持 A / B / 双通道输出
- 可配置强度映射、冷却、持续时间
- 支持强度回落 / 永久叠加模式
- 运行日志中文输出，方便排查
- 支持自定义波形预设

</details>

<details>
<summary><b>[🇬🇧 EN]</b></summary>

- Real-time XInput rumble monitoring
- A / B / Both channel output
- Configurable intensity mapping, cooldown, duration
- Rollback / Permanent strength modes
- Chinese runtime logs for easier debugging
- Custom waveform presets

</details>

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## 📜 更新日志

<details open>
<summary><b>[🇨🇳 中文]</b></summary>

- **v1.6.0** — 正式更名"手柄震动映射"；进程搜索由单次改为周期重试；新增（测试中的）搜索进程功能
- **v1.5.0** — 支持双通道切换、更详细配置、完善运行日志
- **v1.2.5** — 修复配置不生效 bug，增加运行日志支持
- **v1.2.0** — 正式版，支持获取 XInput 震动信息联动设备
- **v1.0** — 测试版，可与 DGHub 握手并控制设备

</details>

<details>
<summary><b>[🇬🇧 EN]</b></summary>

- **v1.6.0** — Renamed to "手柄震动映射"; periodic process searching; new (beta) process finder
- **v1.5.0** — Dual-channel switching, detailed config, improved logs
- **v1.2.5** — Fixed config bug, added runtime logs
- **v1.2.0** — Official release with XInput capture
- **v1.0** — Beta, initial handshake & control

</details>

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## ⚠️ 注意事项

<details open>
<summary><b>[🇨🇳 中文]</b></summary>

- 请通过 DGHub 启动本插件，**不要单独运行 exe**
- 修改进程名后建议重启插件
- 插件运行期间请勿修改配置
- 本插件仅做本地信号映射，不修改游戏文件

</details>

<details>
<summary><b>[🇬🇧 EN]</b></summary>

- Always start the plugin via DGHub; do not run the exe directly
- Restart the plugin after changing the process name
- Do not change settings while the plugin is running
- This plugin only maps signals locally and does not modify game files

</details>

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## 📜 源码说明

<details open>
<summary><b>[🇨🇳 中文]</b></summary>

源代码位于「源代码分支」。使用插件无需下载源码。请转到最新版本对应分支下载正式发布包。

</details>

<details>
<summary><b>[🇬🇧 EN]</b></summary>

Source code is available on the source branch. You do not need the source code to use the plugin. Switch to the latest release branch for the official package.

</details>

---

<div align="right"><a href="#-目录--table-of-contents">⬆ 回到目录 / Back to TOC</a></div>

## ⚖️ 免责声明

<details open>
<summary><b>[🇨🇳 中文]</b></summary>

本插件仅供学习与个人娱乐使用。请确保在合法、安全的前提下使用相关设备，注意电流强度与使用时长，避免意外伤害。

</details>

<details>
<summary><b>[🇬🇧 EN]</b></summary>

This plugin is for learning and personal entertainment only. Use related devices legally and safely. Mind intensity and duration to avoid injury.

</details>

---

<div align="center">

**🎮 让每一次震动都有反馈 · Every rumble deserves feedback 🦊**

</div>

