#  🎮 手柄震动映射  

**手柄一震动，郊狼就放电。** 监听 XInput 震动信号，实时联动 DGHub，驱动 DG-Lab 设备输出沉浸式反馈。


[![Version](https://img.shields.io/badge/version-1.6.0-blue)](https://github.com) [![DGHub](https://img.shields.io/badge/DGHub-v1.8.2%2B-green)](http://www.dghub.top/) [![DGLAB 4.0](https://img.shields.io/badge/DGLAB4.0-v1.0%2B-yellow)](https://dungeon-lab.cn/)

---  
<a id="top"></a>   
## 📑  目录
[插件简介](#about)  
[兼容性说明](#compatibility)  
[更新日志](#changelog)  
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

  
<h2 id="compatibility"></h2>  

#include "docs/compatibility.md"  

[返回目录](#top)  

 <h3 id="changelog"></h3>  

#include "docs/changelog.md"  

[返回目录](#top)  

---  
