"""
DGHub 插件：手柄震动 → 郊狼电击
主路径：XInputSetState（兼容 1.6.0 能工作的游戏）
兜底：Unity IAT + HID DeviceIoControl（静默，不刷诊断）
版本：1.7.2
"""

import asyncio
import json
import os
import time
import threading
import frida
import websockets

config = {
    "min_rumble": 1,
    "cooldown": 0.15,
    "duration": 0.65,
    "strength_scale": 75,
    "min_level": 10,
    "max_level": 95,
    "use_max_motor": True,
    "channel": "both",
    "strength_mode": "rollback",
    "action": "both",
    "preset": "CS2-受伤",
    "process_name": "SlimeRancher2.exe",
}

ws = None
loop = None
last_time = 0
last_time_lock = threading.Lock()
device_connected = True
last_raw_log_time = 0
last_raw_log_lock = threading.Lock()


async def send_log(level: str, message: str):
    if not ws:
        return
    try:
        await ws.send(json.dumps({
            "op": "log",
            "level": level,
            "message": message
        }))
    except Exception:
        pass


async def report_status(text: str):
    if not ws:
        return
    try:
        await ws.send(json.dumps({
            "op": "status",
            "fields": {"display_status": text}
        }))
    except Exception:
        pass


async def trigger_shock(level: int):
    if not ws or not device_connected:
        return
    try:
        payload = {
            "op": "trigger",
            "action": config.get("action", "both"),
            "delta_pct": int(level),
            "strength_mode": config.get("strength_mode", "rollback"),
            "duration_s": float(config.get("duration", 0.65)),
            "preset": config.get("preset", "CS2-受伤"),
            "channel": config.get("channel", "both"),
            "label": "手柄震动 " + str(level) + "%"
        }
        await ws.send(json.dumps(payload))
        mode = "回落" if config.get("strength_mode") == "rollback" else "永久"
        msg = (
            "触发电击 +" + str(level) + "% | 通道:"
            + str(config.get("channel")) + " | 模式:" + mode
        )
        await send_log("info", msg)
        print("[" + time.strftime("%H:%M:%S") + "] " + msg)
    except Exception as e:
        await send_log("error", "发送失败: " + str(e))
        print("发送失败: " + str(e))


def _log_sync(level: str, message: str):
    print("[" + time.strftime("%H:%M:%S") + "] " + message)
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(send_log(level, message), loop)


def _report_status_sync(text: str):
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(report_status(text), loop)


def on_message(message, data):
    global last_time, last_raw_log_time

    if message.get("type") != "send":
        if message.get("type") == "error":
            _log_sync("error", "Frida error: " + str(message.get("description", message)))
        return

    payload = message.get("payload") or {}
    t = payload.get("type")

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
    # 忽略 diag / module 等噪声类型（脚本侧基本不再发送）

    left = int(payload.get("left", 0))
    right = int(payload.get("right", 0))
    src = payload.get("src", "xinput")

    if left > 0 or right > 0:
        with last_raw_log_lock:
            now_log = time.time()
            if now_log - last_raw_log_time >= 0.5:
                last_raw_log_time = now_log
                _log_sync("info", f"原始震动({src}) left={left} right={right}")

    if config.get("use_max_motor", True):
        intensity = max(left, right)
    else:
        intensity = (left + right) // 2

    if intensity < int(config.get("min_rumble", 1)):
        return

    with last_time_lock:
        now = time.time()
        if now - last_time < float(config.get("cooldown", 0.15)):
            return
        last_time = now

    raw_level = int(intensity / 65535.0 * float(config.get("strength_scale", 75)))
    min_level = int(config.get("min_level", 10))
    max_level = int(config.get("max_level", 95))
    level = max(min_level, min(max_level, raw_level))

    if loop and loop.is_running():
        log_msg = f"检测到震动 左={left} 右={right} -> 强度{level}%"
        asyncio.run_coroutine_threadsafe(send_log("info", log_msg), loop)
        asyncio.run_coroutine_threadsafe(trigger_shock(level), loop)


FRIDA_SCRIPT = r"""
'use strict';

var XINPUT_NAMES = [
    'xinput1_4.dll', 'xinput1_3.dll', 'xinput1_2.dll', 'xinput1_1.dll',
    'xinput9_1_0.dll', 'xinputuap.dll', 'xinput.dll',
    'XInput1_4.dll', 'XInput1_3.dll', 'XInput1_2.dll', 'XInput1_1.dll',
    'XInput9_1_0.dll', 'XInputUap.dll', 'XInput.dll'
];

var hookedAddrs = {};
var hookedDlls = {};
var iatDone = false;
var hidDone = false;

function safeFindExport(moduleName, exportName) {
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

function attachSetState(addr, tag, src) {
    if (!addr) return false;
    var key = addr.toString();
    if (hookedAddrs[key]) return true;
    try {
        Interceptor.attach(addr, {
            onEnter: function (args) {
                try {
                    var vib = args[1];
                    if (vib.isNull()) return;
                    var left = vib.readU16();
                    var right = vib.add(2).readU16();
                    send({ left: left, right: right, src: src || 'xinput' });
                } catch (e) {}
            }
        });
        hookedAddrs[key] = true;
        send({ type: 'hooked', dll: tag, addr: key });
        return true;
    } catch (e) {
        return false;
    }
}

function hookOneDll(modName) {
    if (hookedDlls[modName]) return true;
    var addr = safeFindExport(modName, 'XInputSetState');
    if (!addr) addr = safeFindExport(modName, 'XInputSetStateEx');
    if (!addr) {
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

function tryXInput() {
    var any = false;
    var i, mods, m, n;
    for (i = 0; i < XINPUT_NAMES.length; i++) {
        if (hookOneDll(XINPUT_NAMES[i])) any = true;
    }
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

// Unity 主模块 IAT（静默，只在钩成功时打 Hook 日志）
function tryIAT() {
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
    // 模块可能尚未加载，不置 iatDone，允许重试时再扫
    if (any) iatDone = true;
    return any;
}

function hookLoader() {
    function hookOne(exportName, isWide) {
        var exp = safeFindExport('kernel32.dll', exportName);
        if (!exp) return;
        try {
            Interceptor.attach(exp, {
                onEnter: function (args) {
                    this._path = null;
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

// HID 兜底：无诊断日志，仅在解析到非零马达时上报震动
function hookHID() {
    if (hidDone) return;
    var exp = safeFindExport('kernel32.dll', 'DeviceIoControl');
    if (!exp) return;
    try {
        Interceptor.attach(exp, {
            onEnter: function (args) {
                try {
                    var inBuf = args[2];
                    var inSize = args[3].toUInt32();
                    if (inBuf.isNull() || inSize < 4 || inSize > 64) return;
                    var b0 = inBuf.readU8();
                    // Xbox 类输出报告常见 reportId
                    if (b0 !== 0x00 && b0 !== 0x01 && b0 !== 0x03 && b0 !== 0x0d) return;
                    var l8 = inBuf.add(2).readU8();
                    var r8 = inBuf.add(3).readU8();
                    if (l8 === 0 && r8 === 0) return;
                    send({
                        left: l8 * 257,
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

function tryAll() {
    var a = tryXInput();
    var b = tryIAT();
    return a || b;
}

send({ type: 'info', msg: 'Frida 脚本开始（XInput + IAT + HID）' });

var ok0 = false;
try { ok0 = tryAll(); } catch (e) {
    send({ type: 'error', msg: 'tryAll: ' + String(e) });
}
send({ type: 'hook_result', ok: ok0, phase: 'immediate' });

hookLoader();
hookHID();

var n = 0;
var timer = setInterval(function () {
    n++;
    var ok = false;
    try { ok = tryAll(); } catch (e) {}
    if (ok) {
        send({ type: 'hook_result', ok: true, phase: 'retry-' + n });
        clearInterval(timer);
    } else if (n >= 45) {
        // 约 90 秒，给 Unity 更长时间
        send({ type: 'hook_result', ok: false, phase: 'retry-final' });
        clearInterval(timer);
    }
}, 2000);

send({ type: 'info', msg: '监听中' });
"""


def start_frida():
    while True:
        session = None
        try:
            process_name = config.get("process_name", "SlimeRancher2.exe")
            _log_sync("info", "目标进程: " + process_name)
            _report_status_sync("正在查找 " + process_name)

            try:
                session = frida.attach(process_name)
            except Exception as e:
                _log_sync("error", "附加失败: " + str(e) + "，5 秒后重试")
                _report_status_sync("进程未找到，重试中")
                time.sleep(5)
                continue

            _log_sync("info", "Frida 已成功附加")
            _report_status_sync("已附加，注入脚本中")

            detached_event = threading.Event()

            def on_detached(reason):
                _log_sync("warning", "进程已脱离: " + str(reason))
                detached_event.set()

            session.on("detached", on_detached)

            script = session.create_script(FRIDA_SCRIPT)
            script.on("message", on_message)
            script.load()

            _log_sync("info", "脚本已加载，等待震动数据")
            _report_status_sync("监听中")

            while not detached_event.is_set():
                time.sleep(1)

            try:
                session.detach()
            except Exception:
                pass
            _log_sync("info", "重新搜索进程…")
            time.sleep(2)

        except Exception as e:
            _log_sync("error", "Frida 异常: " + str(e) + "，5 秒后重试")
            _report_status_sync("异常，重试中")
            try:
                if session:
                    session.detach()
            except Exception:
                pass
            time.sleep(5)


async def main():
    global ws, loop, device_connected
    loop = asyncio.get_running_loop()

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

        await ws.send(json.dumps({
            "op": "hello",
            "token": token,
            "manifest": {
                "id": "rumble_shock",
                "name": "手柄震动映射",
                "version": "1.7.2",
                "sdk": "1"
            }
        }))

        ack = json.loads(await ws.recv())
        if not ack.get("accepted"):
            print("握手失败: " + str(ack))
            return

        print("插件已连接 DGHub")
        await send_log("info", "插件已连接，等待配置")
        await report_status("已连接，等待配置")

        frida_started = False

        async for msg in ws:
            try:
                data = json.loads(msg)
            except Exception:
                continue

            op = data.get("op")

            if op == "stop":
                await send_log("info", "收到停止指令，退出")
                break

            elif op == "config":
                config.update(data.get("data", {}))
                await send_log("info", "收到全量配置")
                await send_log("info", "目标进程: " + str(config.get("process_name", "")))
                if not frida_started:
                    frida_started = True
                    threading.Thread(target=start_frida, daemon=True).start()

            elif op == "config_changed":
                key = data.get("key")
                value = data.get("value")
                if key in config:
                    config[key] = value
                    await send_log("info", f"配置更新: {key} = {value}")
                    if key == "process_name":
                        await send_log("warning", "进程名已改，请重启插件生效")
                        await report_status("进程名已改，请重启插件")

            elif op == "device_info":
                device_connected = bool(data.get("connected", False))
                status = "设备已连接" if device_connected else "设备未连接"
                await send_log("info", status)
                await report_status(status)

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
