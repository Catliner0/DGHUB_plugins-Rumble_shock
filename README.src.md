#  🎮 手柄震动映射 

> **Change language to** [ English](English.md)  

**手柄一震动，郊狼就放电**   
利用Xinput向手柄发送震动信息的特性，通过frida来获取手柄震动数据基于此向DGHUB发送信息以控制你的DGLAB产品  
`源代码位于「源代码分支」。使用插件无需下载源码。请转到最新版本对应分支下载正式发布包`  
`本插件仅供学习与个人娱乐使用。请确保在合法、安全的前提下使用相关设备，注意电流强度与使用时长，避免意外伤害`  

[![Version](https://img.shields.io/badge/version-1.7.2-blue)](https://github.com) [![DGHub](https://img.shields.io/badge/DGHub-v1.8.2%2B-green)](http://www.dghub.top/) [![DGLAB 4.0](https://img.shields.io/badge/DGLAB4.0-v4.2.2a2478e%2B-yellow)](https://dungeon-lab.cn/)

---  
<a id="top"></a>   
## 📑  目录
- [插件简介](#about)   
- [快速部署](#start)  
- [兼容性说明](#compatibility)   
- [更新日志](#changelog)    
<h4 id="about"></h4>  

## 📖  插件简介  

本插件会挂钩游戏进程中的 `XInputSetState`，实时获取左右马达震动强度，并按你配置的规则映射为电击强度与波形，通过 DGHub 发送给已连接的 DG-Lab 设备  

### 🛠️ 前置软件  
| 软件 | 说明 | 链接 |  
| :--- | :--- | :--- |  
| **DGHub** | 插件运行与设备控制中枢 | [下载](http://www.dghub.top/) |  
| **DG-Lab** | 官方设备与生态 | [下载](https://dungeon-lab.cn/) |  

[返回目录](#top)  

---  
<h5 id="start"></h5>  

## 🚀 快速部署  
**1. 下载与解压**  
本项目采用分卷压缩上传，请下载以下文件并放在同一文件夹：

- `手柄震动联动.7z.001`
- `手柄震动联动.7z.002`
- `手柄震动联动.7z.003`

使用 7-Zip、Bandizip、WinRAR 等解压即可。若解压遇到问题，可使用附带的解压程序 `手柄震动联动.exe` 辅助解压  

**2. 导入插件**  
解压后找到 `main.zip`（插件本体），打开 **DGHub → 插件中心 → 外部插件 → 导入该 zip**  

**3.配置插件**  
在`DGHUB`-`插件中心`-`外部插件`中找到本插件，在插件配置页填写要监听的**游戏进程名**   
`插件运行时无法修改配置 请先停止再调整`

**4.开始使用**    
启动插件并开始游戏   
**确认游戏使用XInput手柄输入并禁用 Steam 输入**

[返回目录](#top) 

---   

<h2 id="compatibility"></h2>  

#include "docs/compatibility.md"  

[返回目录](#top)  

---  

 <h3 id="changelog"></h3>  

#include "docs/changelog.md"  

[返回目录](#top)  

---  
