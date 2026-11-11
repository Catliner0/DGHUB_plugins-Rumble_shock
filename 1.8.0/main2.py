
import asyncio
import json
import os
import time
import threading
import frida          # 插件特有依赖：打包时必须随插件分发（见打包说明）
import websockets     # DGHub 基础依赖：主程序环境已提供

#打包指令：PyInstaller --noconfirm --clean --onedir --console --noupx --name main --collect-all frida main2.py

#默认配置
config = {
    "min_rumble": 1,            # 震动阈值（0~65535），低于此值视为误触
    "cooldown": 0.15,           # 两次电击的最小间隔（秒），防止 60fps 刷屏
    "duration": 0.65,           # 单次电击持续时间（秒），rollback 结束后回落
    "strength_scale": 75,       # 映射比例：马达值 65535 对应多少百分比
    "min_level": 10,            # 强度下限，保证弱震动也有可感知输出
    "max_level": 95,            # 强度上限，避免满强度电击
    "use_max_motor": True,      # True=取左右马达较大值；False=取平均
    "channel": "both",          # 输出通道：a / b / both
    "strength_mode": "rollback",# rollback=播完回落；permanent=永久抬高 baseline
    "action": "both",           # both=强度+波形；strength / waveform
    "preset": "CS2-受伤",        # 波形预设名（由主程序提供的原生预设）
    "process_name": "SlimeRancher2.exe",  # 要附加的目标进程
    "mode":"line" #映射模式
}

#全局变量
ws = None                       # 当前 WebSocket 连接，握手成功后赋值
loop = None                     # asyncio 事件循环，供其他线程投递协程
last_time = 0                   # 上次真正触发电击的时间戳（冷却用）
last_time_lock = threading.Lock()
device_connected = True         # 设备连接状态，由 device_info 消息更新
last_raw_log_time = 0             # 上次打印原始震动日志的时间戳（限流用）
last_raw_log_lock = threading.Lock()
list_intensity=[]
list_intensity_=[]
min_intensity=65535
max_intensity=0

async def send_log(level: str, message: str):#日志发送
    if not ws:
        return
    try:
        await ws.send(json.dumps({
            "op": "log",
            "level": level,#debug / info / warning / error
            "message": message
        }))
    except Exception:
        pass

async def report_status(text: str):#悬浮窗弹幕
    if not ws:
        return
    try:
        await ws.send(json.dumps({
            "op": "status",
            "fields": {"display_status": text}
        }))
    except Exception:
        pass

async def trigger_shock(level: int):#电击指令
    #检测是否断联
    if not ws or not device_connected:
        return
    #发送电击指令
    try:
        payload = {
            "op": "trigger",                                  # 固定值：统一触发消息（强度+波形+通道一条搞定）
            "action": config.get("action", "both"),           # both=同时改强度和播波形；strength/waveform 为单选
            "delta_pct": int(level),                          # 强度增量（%），即本次要加到 baseline 上的值
            "strength_mode": config.get("strength_mode", "rollback"),  # rollback=到时回落；permanent=永久改 baseline
            "duration_s": float(config.get("duration", 0.65)),# 本次强度/波形的持续时间（秒）
            "preset": config.get("preset", "CS2-受伤"),        # 用哪个原生波形预设
            "channel": config.get("channel", "both"),         # 输出到 A / B / 双通道
            "label": "手柄震动映射：" + str(level) + "%"            # 主程序 UI、OBS 上显示的文案
        }
        await ws.send(json.dumps(payload))#发送电击指令
        #发送日志
        mode = "回落" if config.get("strength_mode") == "rollback" else "永久"
        msg = (str(config.get("channel"))+"通道：电击"+ str(level) +"%" + " | 模式:" + mode )
        await send_log("info", msg)
        print("[" + time.strftime("%H:%M:%S") + "] " + msg)
    #异常日志
    except Exception as e:
        await send_log("error", "电击指令发送失败: " + str(e))
        print("电击指令发送失败: " + str(e))

def _log_sync(level: str, message: str):#发送日志_
    #先打控制台，再投递回主线程
    print("[" + time.strftime("%H:%M:%S") + "] " + message)
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(send_log(level, message), loop)

def _report_status_sync(text: str):#悬浮窗弹幕_
    #和日志一样，投递回主线程
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(report_status(text), loop)

def on_message(message, data):#Frida回调消息处理：获取震动信息并映射为电击
    global last_time, last_raw_log_time

    #error信息处理
    if message.get("type") != "send":
        if message.get("type") == "error":
            _log_sync("error", "Frida error: " + str(message.get("description", message)))
        return

    #获取send信息的type类型
    payload = message.get("payload") or {}
    t = payload.get("type")

    if True:#筛除非震动数据send消息
        if t == "hooked":
            _log_sync("info", f"[Hook] 已挂上 {payload.get('dll')} @ {payload.get('addr')}")
            _report_status_sync("已 Hook，等待震动")
            return
        if t == "hook_result":
            ok = payload.get("ok")
            phase = payload.get("phase", "")
            if ok or phase in ("immediate", "retry-final"):
                _log_sync("info" if ok else "warning", f"[Hook] phase={phase} ok={ok}")
            return
        if t == "loadlib":
            _log_sync("info", f"[LoadLibrary] {payload.get('path')}")
            return
        if t == "getproc":
            _log_sync("info", f"[GetProcAddress] {payload.get('name')}")
            return
        if t == "error":
            _log_sync("error", f"[脚本] {payload.get('msg')}")
            return
        if t == "info":
            _log_sync("info", str(payload.get("msg", "")))
            return
        if "left" not in payload and "right" not in payload:
            return

    #获取震动数据：left/right 是 0~65535
    left = int(payload.get("left", 0))
    right = int(payload.get("right", 0))
    src = payload.get("src", "xinput")

    #原始日志限流：1秒一条
    if left > 0 or right > 0:
        with last_raw_log_lock:
            now_log = time.monotonic()
            if now_log - last_raw_log_time >= 1:
                last_raw_log_time = now_log
                _log_sync("info", f"手柄震动[{src}]left={left} right={right}")

    #取强度：默认取较大值
    if config.get("use_max_motor", True):
        intensity = max(left, right)
    else:
        intensity = (left + right) // 2

    #低于阈值忽略
    if intensity < int(config.get("min_rumble", 1)):
        return

    #冷却判断
    with last_time_lock:
        now = time.monotonic()
        if now - last_time < float(config.get("cooldown", 0.15)):
            return
        last_time = now

    #映射到百分比并钳制上下限
    min_level = int(config.get("min_level", 10))
    max_level = int(config.get("max_level", 95))
    if min_level > max_level:
        t=min_level
        min_level=max_level
        max_level=t

    if str(config.get("mode", "line"))=="line":
        raw_level = int(intensity / 65535.0 * float(config.get("strength_scale", 75)))
    elif str(config.get("mode", "line"))=="different" or str(config.get("mode", "line"))=="different_":
        global  list_intensity, min_intensity, max_intensity,list_intensity_,m_
        list_intensity.append(intensity)
        list_intensity_.append(intensity)
        listlen=len(list_intensity)
        if listlen < 11 :
            raw_level = min_level
            if listlen==1 and len(list_intensity_)==0:
                list_intensity_.append(intensity)
        else:
            del list_intensity[0]
            if len(list_intensity_) > 100:
                del list_intensity_[0]
            average = sum(list_intensity)/len(list_intensity)
            different=intensity-average
            if str(config.get("mode", "line"))=="different_":
                ref = 65535.0 * int(config.get("strength_scale", 75)) / 100.0
                raw_level = int(min_level+(max_level-min_level)*(min(1.0,different/max(ref,1.0))))
            else :
                max_intensity = max(list_intensity_)
                min_intensity = min(list_intensity_)
                m = max(max_intensity - min_intensity, 30)
                raw_level = int(different / m * (max_level - min_level) + min_level)


    else:
        _log_sync("error","映射模式异常")
        return
    level = max(min_level, min(max_level, raw_level))

    #投递回 asyncio 线程发送
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(trigger_shock(level), loop)

#注入到目标进程的脚本：XInput 主路径 + IAT + HID 三重兜底
FRIDA_SCRIPT = r"""
'use strict';

//常见 xinput DLL 名（大小写不统一，两种都列）
var XINPUT_NAMES = [
    'xinput1_4.dll', 'xinput1_3.dll', 'xinput1_2.dll', 'xinput1_1.dll',
    'xinput9_1_0.dll', 'xinputuap.dll', 'xinput.dll',
    'XInput1_4.dll', 'XInput1_3.dll', 'XInput1_2.dll', 'XInput1_1.dll',
    'XInput9_1_0.dll', 'XInputUap.dll', 'XInput.dll'
];

var hookedAddrs = {};   //已挂地址，去重
var hookedDlls = {};    //已处理模块
var iatDone = false;    //IAT 是否已挂上
var hidDone = false;    //HID 探针是否已装

function safeFindExport(moduleName, exportName) {   //查找导出地址（Frida 16/17 兼容）
    var addr = null;
    try {
        if (typeof Module.findExportByName === 'function') {
            addr = Module.findExportByName(moduleName, exportName);
            if (addr) return addr;
        }
    } catch (e) {}
    try {
        if (typeof Module.getExportByName === 'function') {
            addr = Module.getExportByName(moduleName, exportName);
            if (addr) return addr;
        }
    } catch (e) {}
    try {
        var mod = Process.findModuleByName(moduleName);
        if (!mod) return null;
        if (typeof mod.findExportByName === 'function') {
            addr = mod.findExportByName(exportName);
            if (addr) return addr;
        }
        if (typeof mod.enumerateExports === 'function') {
            var list = mod.enumerateExports();
            for (var i = 0; i < list.length; i++) {
                if (list[i].name === exportName) return list[i].address;
            }
        }
    } catch (e) {}
    return null;
}

function attachSetState(addr, tag, src) {   //挂 XInputSetState，只读参数
    if (!addr) return false;
    var key = addr.toString();
    if (hookedAddrs[key]) return true;   //已挂过
    try {
        Interceptor.attach(addr, {
            onEnter: function (args) {
                try {
                    var vib = args[1];
                    if (vib.isNull()) return;   //空指针
                    var left = vib.readU16();      //左马达
                    var right = vib.add(2).readU16();   //右马达
                    send({ left: left, right: right, src: src || 'xinput' });
                } catch (e) {}
            }
        });
        hookedAddrs[key] = true;
        send({ type: 'hooked', dll: tag, addr: key });   //通知 Python 侧
        return true;
    } catch (e) {
        return false;
    }
}

function hookOneDll(modName) {   //给单个模块挂 XInputSetState
    if (hookedDlls[modName]) return true;
    var addr = safeFindExport(modName, 'XInputSetState');
    if (!addr) addr = safeFindExport(modName, 'XInputSetStateEx');
    if (!addr) {
        //兜底：遍历导出表，兼容按序号导出
        try {
            var mod = Process.findModuleByName(modName);
            if (mod && typeof mod.enumerateExports === 'function') {
                var list = mod.enumerateExports();
                for (var i = 0; i < list.length; i++) {
                    var n = list[i].name;
                    if (n === 'XInputSetState' || n === 'XInputSetStateEx' ||
                        n === '3' || n === '#3') {
                        addr = list[i].address;
                        break;
                    }
                }
            }
        } catch (e) {}
    }
    if (!addr) return false;
    if (attachSetState(addr, modName, 'xinput')) {
        hookedDlls[modName] = true;
        return true;
    }
    return false;
}

function tryXInput() {   //XInput 主路径
    var any = false;
    var i, mods, m, n;
    for (i = 0; i < XINPUT_NAMES.length; i++) {
        if (hookOneDll(XINPUT_NAMES[i])) any = true;
    }
    //再扫一遍进程里名字带 xinput 的模块
    try {
        mods = Process.enumerateModules();
        for (i = 0; i < mods.length; i++) {
            m = mods[i];
            n = (m.name || '').toLowerCase();
            if (n.indexOf('xinput') !== -1) {
                if (hookOneDll(m.name)) any = true;
            }
        }
    } catch (e) {}
    return any;
}

function tryIAT() {   //Unity IAT 兜底
    if (iatDone) return false;
    var targets = ['UnityPlayer.dll', 'GameAssembly.dll', 'SlimeRancher2.exe'];
    var any = false;
    for (var t = 0; t < targets.length; t++) {
        var mod = Process.findModuleByName(targets[t]);
        if (!mod || typeof mod.enumerateImports !== 'function') continue;
        var imps;
        try { imps = mod.enumerateImports(); } catch (e) { continue; }
        for (var i = 0; i < imps.length; i++) {
            var imp = imps[i];
            var iname = imp.name || '';
            if (iname === 'XInputSetState' || iname === 'XInputSetStateEx') {
                if (imp.address && attachSetState(imp.address, 'IAT:' + targets[t], 'iat')) {
                    any = true;
                }
            }
        }
    }
    //模块可能还没加载，失败不置 iatDone，允许重扫
    if (any) iatDone = true;
    return any;
}

function hookLoader() {   //LoadLibrary/GetProcAddress 探针
    //给单个 LoadLibrary 变体挂钩子
    function hookOne(exportName, isWide) {
        var exp = safeFindExport('kernel32.dll', exportName);
        if (!exp) return;
        try {
            Interceptor.attach(exp, {
                onEnter: function (args) {
                    this._path = null;   //留给 onLeave 用
                    try {
                        this._path = isWide ? args[0].readUtf16String() : args[0].readUtf8String();
                    } catch (e) {}
                },
                onLeave: function () {
                    if (!this._path) return;
                    var p = this._path.toLowerCase();
                    if (p.indexOf('xinput') !== -1) {
                        send({ type: 'loadlib', path: this._path });
                        tryXInput();
                        tryIAT();
                    }
                }
            });
        } catch (e) {}
    }
    hookOne('LoadLibraryW', true);
    hookOne('LoadLibraryExW', true);
    hookOne('LoadLibraryA', false);
    hookOne('LoadLibraryExA', false);

    //GetProcAddress 兜底
    var gpa = safeFindExport('kernel32.dll', 'GetProcAddress');
    if (gpa) {
        try {
            Interceptor.attach(gpa, {
                onEnter: function (args) {
                    this._name = null;
                    try { this._name = args[1].readAnsiString(); } catch (e) {
                        try { this._name = args[1].readUtf8String(); } catch (e2) {}
                    }
                },
                onLeave: function (retval) {
                    if (!this._name || retval.isNull()) return;
                    if (this._name === 'XInputSetState' || this._name === 'XInputSetStateEx') {
                        send({ type: 'getproc', name: this._name });
                        attachSetState(retval, 'GPA:' + this._name, 'xinput');
                    }
                }
            });
        } catch (e) {}
    }
}

function hookHID() {   //HID 兜底（静默）
    if (hidDone) return;
    var exp = safeFindExport('kernel32.dll', 'DeviceIoControl');
    if (!exp) return;
    try {
        Interceptor.attach(exp, {
            onEnter: function (args) {
                try {
                    var inBuf = args[2];              //lpInBuffer
                    var inSize = args[3].toUInt32();  //nInBufferSize
                    if (inBuf.isNull() || inSize < 4 || inSize > 64) return;
                    var b0 = inBuf.readU8();
                    //Xbox 类输出报告常见 reportId
                    if (b0 !== 0x00 && b0 !== 0x01 && b0 !== 0x03 && b0 !== 0x0d) return;
                    var l8 = inBuf.add(2).readU8();   //左马达 8 位
                    var r8 = inBuf.add(3).readU8();   //右马达 8 位
                    if (l8 === 0 && r8 === 0) return;
                    send({
                        left: l8 * 257,               //8 位转 16 位
                        right: r8 * 257,
                        src: 'hid'
                    });
                } catch (e) {}
            }
        });
        hidDone = true;
        send({ type: 'hooked', dll: 'DeviceIoControl(HID)', addr: exp.toString() });
    } catch (e) {}
}

function tryAll() {   //一次完整探测
    var a = tryXInput();
    var b = tryIAT();
    return a || b;
}

//脚本入口：先探测一次，再布探针 + 定时重试
send({ type: 'info', msg: 'Frida 脚本开始（XInput + IAT + HID）' });

//首次探测
var ok0 = false;
try { ok0 = tryAll(); } catch (e) {
    send({ type: 'error', msg: 'tryAll: ' + String(e) });
}
send({ type: 'hook_result', ok: ok0, phase: 'immediate' });

//等模块出现的两个探针
hookLoader();
hookHID();

//定时重试：2 秒一次，最多 45 次（约 90 秒）
var n = 0;
var timer = setInterval(function () {
    n++;
    var ok = false;
    try { ok = tryAll(); } catch (e) {}
    if (ok) {
        send({ type: 'hook_result', ok: true, phase: 'retry-' + n });
        clearInterval(timer);
    } else if (n >= 45) {
        send({ type: 'hook_result', ok: false, phase: 'retry-final' });
        clearInterval(timer);
    }
}, 2000);

send({ type: 'info', msg: '监听中' });
"""

def start_frida():#Frida后台线程
    #循环重试
    while True:
        session = None   #每轮重置
        try:
            #取目标进程名
            process_name = config.get("process_name", "SlimeRancher2.exe")
            _log_sync("info", "目标进程: " + process_name)
            _report_status_sync("正在查找 " + process_name)

            #附加进程，失败等 5 秒
            try:
                session = frida.attach(process_name)
            except Exception as e:
                _log_sync("error", "附加失败: " + str(e) + "，5 秒后重试")
                _report_status_sync("进程未找到，重试中")
                time.sleep(5)
                continue

            _log_sync("info", "Frida 已成功附加")
            _report_status_sync("已附加，注入脚本中")

            #用 Event 跨线程等待
            detached_event = threading.Event()

            def on_detached(reason):#进程脱离回调
                _log_sync("warning", "进程已脱离: " + str(reason))
                detached_event.set()

            session.on("detached", on_detached)

            #加载注入脚本
            script = session.create_script(FRIDA_SCRIPT)
            script.on("message", on_message)
            script.load()

            _log_sync("info", "脚本已加载，等待震动数据")
            _report_status_sync("监听中")

            #阻塞等待脱离
            while not detached_event.is_set():
                time.sleep(1)

            #清理旧会话，回去重新找进程
            try:
                session.detach()
            except Exception:
                pass
            _log_sync("info", "重新搜索进程…")
            time.sleep(2)

        #兜底：线程不能死
        except Exception as e:
            _log_sync("error", "Frida 异常: " + str(e) + "，5 秒后重试")
            _report_status_sync("异常，重试中")
            try:
                if session:
                    session.detach()
            except Exception:
                pass
            time.sleep(5)

async def main():#插件入口
    global ws, loop, device_connected
    loop = asyncio.get_running_loop()   #供 Frida 线程投递协程

    #读启动参数
    host = os.environ.get("DGHUB_HOST", "127.0.0.1")
    port = os.environ.get("DGHUB_PORT")
    token = os.environ.get("DGHUB_TOKEN")

    if not port or not token:
        print("缺少 DGHUB_PORT 或 DGHUB_TOKEN，请通过 DGHub 启动本插件")
        return

    uri = f"ws://{host}:{port}/ws/plugin?token={token}"
    print("正在连接 DGHub: " + uri)

    async with websockets.connect(uri) as websocket:
        ws = websocket

        #握手
        await ws.send(json.dumps({
            "op": "hello",
            "token": token,
            "manifest": {
                "id": "rumble_shock",
                "name": "手柄震动映射",
                "version": "1.8.0",
                "sdk": "1"
            }
        }))

        #握手结果
        ack = json.loads(await ws.recv())
        if not ack.get("accepted"):
            print("握手失败: " + str(ack))
            return

        print("插件已连接 DGHub")
        await send_log("info", "插件已连接，等待配置")
        await report_status("已连接，等待配置")

        frida_started = False   #Frida 线程只启动一次

        #消息循环
        async for msg in ws:
            try:
                data = json.loads(msg)
            except Exception:
                continue

            op = data.get("op")

            #停止
            if op == "stop":
                await send_log("info", "收到停止指令，退出")
                break

            #全量配置
            elif op == "config":
                config.update(data.get("data", {}))
                await send_log("info", "目标进程: " + str(config.get("process_name", "")))
                #第一份配置到齐后再启动 Frida
                if not frida_started:
                    frida_started = True
                    threading.Thread(target=start_frida, daemon=True).start()

            #配置变更
            elif op == "config_changed":
                key = data.get("key")
                value = data.get("value")
                if key in config:
                    config[key] = value
                    await send_log("info", f"配置更新: {key} = {value}")
                    #进程名改了要重启才生效
                    if key == "process_name":
                        await send_log("warning", "进程名已改，请重启插件生效")
                        await report_status("进程名已改，请重启插件")

            #设备状态
            elif op == "device_info":
                device_connected = bool(data.get("connected", False))
                status = "设备已连接" if device_connected else "设备未连接"
                await send_log("info", status)
                await report_status(status)

            #心跳
            elif op == "ping":
                try:
                    await ws.send(json.dumps({"op": "pong", "t": data.get("t")}))
                except Exception:
                    pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("插件已停止")
