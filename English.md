#  🎮 Gamepad Vibration Mapping 

> **切换语言为** [ 中文](README.md)  

**Gamepad vibrates, Coyote zaps**   
Leveraging the XInput feature that sends vibration data to gamepads, this tool uses Frida to capture vibration intensity and forwards it to DGHub to control your DG-Lab device.  
`The source code is located in the "源代码" branch. You do not need to download the source code to use the plugin. Please navigate to the branch corresponding to the latest release to download the official build.`  
`This plugin is intended solely for learning and personal entertainment. Please ensure you use related devices legally and safely. Pay attention to current intensity and usage duration to avoid accidental injury.`  

[![Version](https://img.shields.io/badge/version-1.7.2-blue)](https://github.com) [![DGHub](https://img.shields.io/badge/DGHub-v1.8.2%2B-green)](http://www.dghub.top/) [![DGLAB 4.0](https://img.shields.io/badge/DGLAB4.0-v4.2.2a2478e%2B-yellow)](https://dungeon-lab.cn/)

---  
<a id="top"></a>   
## 📑  Table of Contents
- [About](#about)   
- [Quick Start](#start)  
- [Compatibility](#compatibility)   
- [Changelog](#changelog)  

---    
  
<h4 id="about"></h4>  

## 📖  About  

This plugin hooks into the `XInputSetState` function within the game process to capture real-time left and right motor vibration intensity. It then maps this data to shock intensity and waveforms based on your configured rules, sending the signals via DGHub to connected DG-Lab devices.  

### 🛠️  Prerequisites  
| Software | Description | Link |  
| :--- | :--- | :--- |  
| **DGHub** | Plugin runtime & device control hub | [Download](http://www.dghub.top/) |  
| **DG-Lab** | Official devices & ecosystem | [Download](https://dungeon-lab.cn/) |  

[Back to Top](#top)  

---  
<h5 id="start"></h5>  

## 🚀  Quick Start  
**1. Download & Extract**  
This project is uploaded in split archives. Please download the following files and place them in the same folder:

- `GamepadVibrationMapping.7z.001`
- `GamepadVibrationMapping.7z.002`
- `GamepadVibrationMapping.7z.003`

Extract using 7-Zip, Bandizip, WinRAR, or similar tools. If you encounter extraction issues, you can use the included extractor `GamepadVibrationMapping.exe` to assist.  

**2. Import Plugin**  
After extraction, locate `main.zip` (the plugin itself). Open **DGHub → Plugin Center → External Plugins → Import this zip**.  

**3. Configure Plugin**  
Find this plugin in `DGHub` → `Plugin Center` → `External Plugins`. Enter the **game process name** you wish to monitor in the plugin configuration page.   
`Configuration cannot be modified while the plugin is running. Please stop the plugin before adjusting settings.`

**4. Start Using**    
Launch the plugin and start the game.   
**Ensure the game uses XInput gamepad input and Steam Input is disabled.**

[Back to Top](#top) 

---   

<h2 id="compatibility"></h2>  

## 🧩  Compatibility   
Theoretically, it supports all games that control gamepad vibration via XInput. Actual compatibility varies by game and is subject to verification.  
**You must use an XInput-compatible gamepad and disable Steam Input.**

### Verified Compatible Games

| Game | Process Name | Compatibility | Tested Plugin Version | Notes |       
| :--- | :--- | :--- | :--- | :--- |     
| Outer Wilds | `OuterWilds.exe`  | Perfect | 1.6.0 | None  |     
| Death Stranding Director's Cut | `ds.exe` | Fair |  1.6.0| Plugin may be killed if DGHub runs in the background |     
| Monster Hunter Rise |`MonsterHunterRise.exe` | Perfect | 1.6.0 |  None |    
| A Dance of Fire and Ice | `N/A` | Not Supported | 1.6.0 | Game does not send vibration data to the gamepad |   
| Slime Rancher 2 | `SlimeRancher2.exe` | Perfect | 1.7.2 | Compatible from version 1.7.2 onwards |  

  

[Back to Top](#top)  

---  

 <h3 id="changelog"></h3>  

## 📜  Changelog  
__v1.0 Beta__    
>1. Able to handshake with DGHub and control DG-Lab devices

__v1.2.0 Release__  
>1. Added support for capturing XInput vibration data to synchronize with DG-Lab devices

__v1.2.5 Update__   
>1. Fixed a bug where configuration settings failed to apply  
>2. Added runtime logging support within the DGHub software

__v1.5.0 Update__  
>1. Added dual-channel switching support  
>2. More detailed configuration options  
>3. Improved DGHub runtime logging

__v1.6.0 Update__   
>1. Officially renamed the plugin to "Gamepad Vibration Mapping"  
>2. Changed startup behavior: previously searched for the process only once; now the plugin periodically retries searching for the process    
>3. Added a process search feature to help you find the game process name (this feature is currently unstable and still in testing)  

__v1.7.2 Update__   
>1. Removed the process search feature  
>2. Added HID DeviceIoControl hooking for vibration data, expanding plugin compatibility   
  

[Back to Top](#top)  

---  