#  🎮 Rumble · Shock   

> **更改语言为** [中文](README.md)  

**When the gamepad vibrates, the coyote strikes.** Listens to XInput vibration signals, syncs with DGHub in real-time, and drives DG-Lab devices to output immersive feedback.  
`Source code is located in the "源代码" branch. Plugin users do not need to download source code. Please go to the latest version's corresponding branch to download the official release package.`  
`This plugin is for learning and personal entertainment purposes only. Please ensure you use related devices in a legal and safe manner, pay attention to current intensity and usage duration, and avoid accidental injuries.`  

[![Version](https://img.shields.io/badge/version-1.6.0-blue)](https://github.com) [![DGHub](https://img.shields.io/badge/DGHub-v1.8.2%2B-green)](http://www.dghub.top/) [![DGLAB 4.0](https://img.shields.io/badge/DGLAB4.0-v4.2.2.a2478e%2B-yellow)](https://dungeon-lab.cn/)

---  
<a id="top"></a>   
## 📑 Table of Contents
- [Plugin Introduction](#about)   
- [Quick Deployment](#start)  
- [Compatibility Notes](#compatibility)   
- [Changelog](#changelog)    
<h4 id="about"></h4>  

## 📖 Plugin Introduction  

This plugin hooks into `XInputSetState` in the game process, retrieves left and right motor vibration intensity in real-time, and maps them to electroshock intensity and waveforms according to your configured rules, sending them via DGHub to connected DG-Lab devices.  

### 🛠️ Prerequisites  
| Software | Description | Link |  
| :--- | :--- | :--- |  
| **DGHub** | Plugin runtime and device control hub | [Download](http://www.dghub.top/) |  
| **DG-Lab** | Official device and ecosystem | [Download](https://dungeon-lab.cn/) |  

[Back to Top](#top)  

---  
<h5 id="start"></h5>  

## 🚀 Quick Deployment  
**1. Download and Extract**  
This project is uploaded in split archives. Please download the following files and place them in the same folder:

- `GamepadVibrationMapping.7z.001`
- `GamepadVibrationMapping.7z.002`
- `GamepadVibrationMapping.7z.003`

Use 7-Zip, Bandizip, WinRAR or similar to extract. If you encounter extraction issues, you can use the included extractor program `GamepadVibrationMapping.exe` to assist.  

**2. Import Plugin**  
After extraction, locate `main.zip` (the plugin itself), open **DGHub → Plugin Center → External Plugins → Import this zip**  

**3. Configure Plugin**  
In `DGHUB` → `Plugin Center` → `External Plugins`, find this plugin. In the plugin configuration page, fill in the **game process name** you want to monitor.  
`Plugin configuration cannot be modified while running. Please stop the plugin first before making adjustments.`

**4. Start Using**  
Launch the plugin and start the game.  
**Confirm the game uses XInput gamepad input and disable Steam Input.**

[Back to Top](#top) 

---   

<h2 id="compatibility"></h2>  

## 🧩 Compatibility Notes   
In theory, all games that control gamepad vibration via XInput are supported. Actual compatibility varies by game implementation and must be verified individually.  
**You must use an XInput-compatible gamepad and disable Steam Input.**

### Verified Compatible Games

| Game | Process Name | Compatibility | Notes |       
| :--- | :--- | :--- | :--- |  
| Outer Wilds | `OuterWilds.exe` | Perfect | None |     
| Death Stranding Director's Cut | `ds.exe` | Fair | Plugin may be killed when DGHUB runs in background |     
| Monster Hunter: Rise | `MonsterHunterRise.exe` | Perfect | None |    
| A Dance of Fire and Ice | `N/A` | Not Supported | Game does not send vibration data to gamepad | 

  

[Back to Top](#top)  

---  

 <h3 id="changelog"></h3>  

## 📜 Changelog  
__v1.0 Beta__    
> 1. Can handshake with DGHUB and control DG-Lab devices

__v1.2.0 Release__  
> 1. Supports retrieving XInput vibration data sent to gamepad to sync with DG-Lab devices

__v1.2.5 Update__   
> 1. Fixed bug where configuration changes were not taking effect  
> 2. Added runtime log support within DGHUB software

__v1.5.0 Update__  
> 1. Supports dual-channel switching  
> 2. More detailed configuration options  
> 3. Improved DGHUB runtime logs

__v1.6.0 Update__   
> 1. Officially renamed plugin to "Gamepad Vibration Mapping"  
> 2. Changed startup behavior: instead of searching for processes only once, the plugin now periodically retries process discovery    
> 3. Added process search feature to help find game process names (this feature is currently unstable and still in testing)  

  

[Back to Top](#top)  

---
