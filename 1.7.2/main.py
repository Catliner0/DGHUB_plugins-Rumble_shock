"""
DGHub 插件：手柄震动 → 郊狼电击
兼容增强：导出扫描 + Unity IAT + HID DeviceIoControl
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
        await ws.send(json.dumps({"op": "log", "level": level, "message": message}))
    except Exception:
        pass


async def report_status(text: str):
    if not ws:
        return
    try:
        await ws.send(json.dumps({"op": "status", "fields": {"display_status": text}}))
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
            "label": "手柄震动 " + str(level) + "%",
        }
        await ws.send(json.dumps(payload))
        mode = "回落" if config.get("strength_mode") == "rollback" else "永久"
        msg = f"触发电击 +{level}% | 通道:{config.get('channel')} | 模式:{mode}"
        await send_log("info", msg)
        print("[" + time.strftime("%H:%M:%S") + "] " + msg)
    except Exception as e:
        await send_log("error", "发送失败: " + str(e))


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

    if t in ("hooked", "hook_result", "module", "diag", "loadlib", "getproc", "info", "error", "hid"):
        if t == "hooked":
            _log_sync("info", f"[Hook] 已挂上 {payload.get('dll')} @ {payload.get('addr')}")
            _report_status_sync("已 Hook，等待震动")
        elif t == "hook_result":
            ok = payload.get("ok")
            _log_sync("info" if ok else "warning", f"[Hook] phase={payload.get('phase')} ok={ok}")
        elif t == "module":
            _log_sync("info", f"[模块] {payload.get('name')}")
        elif t == "diag":
            _log_sync("info", f"[诊断] {payload.get('msg')}")
        elif t == "loadlib":
            _log_sync("info", f"[LoadLibrary] {payload.get('path')}")
        elif t == "getproc":
            _log_sync("info", f"[GetProcAddress] {payload.get('name')}")
        elif t == "hid":
            _log_sync("info", f"[HID] {payload.get('msg')}")
        elif t == "error":
            _log_sync("error", f"[脚本] {payload.get('msg')}")
        elif t == "info":
            _log_sync("info", str(payload.get("msg", "")))
        return

    left = int(payload.get("left", 0))
    right = int(payload.get("right", 0))

    if left > 0 or right > 0:
        with last_raw_log_lock:
            now_log = time.time()
            if now_log - last_raw_log_time >= 0.5:
                last_raw_log_time = now_log
                src = payload.get("src", "xinput")
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
    level = max(int(config.get("min_level", 10)), min(int(config.get("max_level", 95)), raw_level))

    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(
            send_log("info", f"检测到震动 左={left} 右={right} -> 强度{level}%"), loop
        )
        asyncio.run_coroutine_threadsafe(trigger_shock(level), loop)


FRIDA_SCRIPT = r"""
'use strict';

var hookedAddrs = {};
var KEYWORDS = ['xinput', 'setstate', 'rumble', 'motor', 'vibration', 'vibrate', 'ffb', 'forcefeedback'];

function already(addr) {
    var k = addr.toString();
    if (hookedAddrs[k]) return true;
    hookedAddrs[k] = true;
    return false;
}

function attachXInputLike(addr, tag) {
    if (!addr || already(addr)) return false;
    try {
        Interceptor.attach(addr, {
            onEnter: function (args) {
                try {
                    // XInputSetState(dwUserIndex, XINPUT_VIBRATION*)
                    var vib = args[1];
                    if (vib.isNull()) return;
                    var left = vib.readU16();
                    var right = vib.add(2).readU16();
                    send({ left: left, right: right, src: tag });
                } catch (e) {}
            }
        });
        send({ type: 'hooked', dll: tag, addr: addr.toString() });
        return true;
    } catch (e) {
        send({ type: 'error', msg: 'attach ' + tag + ': ' + String(e) });
        hookedAddrs[addr.toString()] = false;
        return false;
    }
}

function safeFindExport(moduleName, exportName) {
    try {
        if (typeof Module.findExportByName === 'function') {
            var a = Module.findExportByName(moduleName, exportName);
            if (a) return a;
        }
    } catch (e) {}
    try {
        if (typeof Module.getExportByName === 'function') {
            var b = Module.getExportByName(moduleName, exportName);
            if (b) return b;
        }
    } catch (e) {}
    try {
        var mod = Process.findModuleByName(moduleName);
        if (mod && typeof mod.enumerateExports === 'function') {
            var list = mod.enumerateExports();
            for (var i = 0; i < list.length; i++) {
                if (list[i].name === exportName) return list[i].address;
            }
        }
    } catch (e) {}
    return null;
}

function nameLooksUseful(n) {
    if (!n) return false;
    var s = n.toLowerCase();
    for (var i = 0; i < KEYWORDS.length; i++) {
        if (s.indexOf(KEYWORDS[i]) !== -1) return true;
    }
    return false;
}

// 1) 具名 XInput DLL
function hookKnownXInput() {
    var names = [
        'xinput1_4.dll', 'xinput1_3.dll', 'xinput1_2.dll', 'xinput1_1.dll',
        'xinput9_1_0.dll', 'xinputuap.dll', 'xinput.dll',
        'XInput1_4.dll', 'XInput1_3.dll', 'XInput9_1_0.dll', 'XInput.dll'
    ];
    var any = false;
    for (var i = 0; i < names.length; i++) {
        var a = safeFindExport(names[i], 'XInputSetState');
        if (!a) a = safeFindExport(names[i], 'XInputSetStateEx');
        if (a && attachXInputLike(a, names[i])) any = true;
    }
    return any;
}

// 2) 全模块导出扫描（名字像 rumble / XInputSetState）
function scanAllExports() {
    var any = false;
    try {
        var mods = Process.enumerateModules();
        for (var i = 0; i < mods.length; i++) {
            var mod = mods[i];
            var mname = mod.name || '';
            var low = mname.toLowerCase();
            if (low.indexOf('xinput') !== -1) {
                send({ type: 'module', name: mname });
            }
            if (typeof mod.enumerateExports !== 'function') continue;
            var exps;
            try { exps = mod.enumerateExports(); } catch (e) { continue; }
            for (var j = 0; j < exps.length; j++) {
                var en = exps[j].name || '';
                if (en === 'XInputSetState' || en === 'XInputSetStateEx') {
                    if (attachXInputLike(exps[j].address, mname + '!' + en)) any = true;
                } else if (nameLooksUseful(en) && low.indexOf('xinput') !== -1) {
                    send({ type: 'diag', msg: '可疑导出 ' + mname + '!' + en });
                }
            }
        }
    } catch (e) {
        send({ type: 'error', msg: 'scanAllExports: ' + String(e) });
    }
    return any;
}

// 3) Unity / 游戏主模块 IAT：若已绑定 XInputSetState 则直接钩导入地址
function hookIAT() {
    var targets = ['UnityPlayer.dll', 'GameAssembly.dll', 'SlimeRancher2.exe', 'Unity.exe'];
    var any = false;
    for (var t = 0; t < targets.length; t++) {
        var mod = Process.findModuleByName(targets[t]);
        if (!mod || typeof mod.enumerateImports !== 'function') continue;
        var imps;
        try { imps = mod.enumerateImports(); } catch (e) { continue; }
        for (var i = 0; i < imps.length; i++) {
            var imp = imps[i];
            var iname = imp.name || '';
            var imod = (imp.module || '').toLowerCase();
            if (iname === 'XInputSetState' || iname === 'XInputSetStateEx' ||
                (imod.indexOf('xinput') !== -1 && nameLooksUseful(iname))) {
                send({ type: 'diag', msg: 'IAT ' + targets[t] + ' <- ' + imp.module + '!' + iname });
                if (imp.address && attachXInputLike(imp.address, 'IAT:' + targets[t] + '!' + iname)) {
                    any = true;
                }
            }
        }
    }
    return any;
}

// 4) LoadLibrary / GetProcAddress
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
                    if (p.indexOf('xinput') !== -1 || p.indexOf('gameinput') !== -1) {
                        send({ type: 'loadlib', path: this._path });
                        tryAll();
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
                        attachXInputLike(retval, 'GPA:' + this._name);
                    }
                }
            });
        } catch (e) {}
    }
}

// 5) HID DeviceIoControl：Xbox 手柄震动输出报告常见为 0x0D 开头、含左右马达字节
function hookHID() {
    var exp = safeFindExport('kernel32.dll', 'DeviceIoControl');
    if (!exp) {
        send({ type: 'diag', msg: '未找到 DeviceIoControl，跳过 HID 钩子' });
        return;
    }
    try {
        Interceptor.attach(exp, {
            onEnter: function (args) {
                try {
                    // BOOL DeviceIoControl(hDevice, dwIoControlCode, lpInBuffer, nInBufferSize, ...)
                    var code = args[1].toUInt32();
                    var inBuf = args[2];
                    var inSize = args[3].toUInt32();
                    // IOCTL_HID_SET_OUTPUT_REPORT 常见值 0x000b000c / 厂商自定义
                    if (inBuf.isNull() || inSize < 3 || inSize > 64) return;
                    // 粗过滤：像 Xbox 有线/无线输出报告
                    var b0 = inBuf.readU8();
                    // 很多 Xbox 震动报告 reportId=0x00/0x01/0x0D，后面带 left/right
                    if (inSize >= 5 && (b0 === 0x00 || b0 === 0x01 || b0 === 0x0d || b0 === 0x03)) {
                        var left = inBuf.add(2).readU8() * 257;  // 0-255 → 约 0-65535
                        var right = inBuf.add(3).readU8() * 257;
                        if (left > 0 || right > 0) {
                            send({ left: left, right: right, src: 'hid' });
                            send({ type: 'hid', msg: 'ioctl=0x' + code.toString(16) + ' size=' + inSize +
                                ' left8=' + inBuf.add(2).readU8() + ' right8=' + inBuf.add(3).readU8() });
                        }
                    }
                } catch (e) {}
            }
        });
        send({ type: 'info', msg: '已挂 DeviceIoControl（HID 兜底）' });
    } catch (e) {
        send({ type: 'error', msg: 'hook HID: ' + String(e) });
    }
}

function diagnose() {
    var hits = [];
    var hasX = false;
    try {
        var mods = Process.enumerateModules();
        for (var i = 0; i < mods.length; i++) {
            var n = mods[i].name || '';
            var l = n.toLowerCase();
            if (l.indexOf('xinput') !== -1 || l.indexOf('gameinput') !== -1 ||
                l.indexOf('dinput') !== -1 || l.indexOf('hid') !== -1 ||
                l.indexOf('unity') !== -1 || l.indexOf('gameassembly') !== -1 ||
                l.indexOf('steam') !== -1 || l.indexOf('input') !== -1) {
                hits.push(n);
                if (l.indexOf('xinput') !== -1) hasX = true;
            }
        }
    } catch (e) {}
    send({ type: 'diag', msg: '相关模块(' + hits.length + '): ' + hits.join(', ') });
    if (!hasX) {
        send({
            type: 'diag',
            msg: '无 xinput*.dll。将依赖 IAT/HID/后续 LoadLibrary。若始终无数据，建议使用游戏目录 XInput 代理 DLL。'
        });
    }
    return hasX;
}

function tryAll() {
    var a = hookKnownXInput();
    var b = scanAllExports();
    var c = hookIAT();
    return a || b || c;
}

send({ type: 'info', msg: 'Frida 兼容增强脚本启动' });
diagnose();
var ok0 = false;
try { ok0 = tryAll(); } catch (e) {
    send({ type: 'error', msg: 'tryAll: ' + String(e) });
}
send({ type: 'hook_result', ok: ok0, phase: 'immediate' });
hookLoader();
hookHID();

var n = 0;
setInterval(function () {
    n++;
    var ok = false;
    try { ok = tryAll(); } catch (e) {}
    if (ok) send({ type: 'hook_result', ok: true, phase: 'retry-' + n });
    else if (n % 5 === 0) {
        send({ type: 'hook_result', ok: false, phase: 'retry-' + n });
        diagnose();
    }
}, 2000);

send({ type: 'info', msg: '监听中：XInput / IAT / LoadLibrary / GetProcAddress / HID' });
"""


def start_frida():
    while True:
        session = None
        try:
            process_name = config.get("process_name", "SlimeRancher2.exe")
            _log_sync("info", "目标进程: " + process_name)
            _log_sync("info", "兼容模式：XInput + IAT + HID")
            _report_status_sync("正在查找 " + process_name)

            try:
                session = frida.attach(process_name)
            except Exception as e:
                _log_sync("error", "附加失败: " + str(e) + "，5 秒后重试")
                time.sleep(5)
                continue

            _log_sync("info", "Frida 已成功附加")
            detached_event = threading.Event()

            def on_detached(reason):
                _log_sync("warning", "进程已脱离: " + str(reason))
                detached_event.set()

            session.on("detached", on_detached)
            script = session.create_script(FRIDA_SCRIPT)
            script.on("message", on_message)
            script.load()
            _log_sync("info", "脚本已加载")
            _report_status_sync("监听中（XInput/IAT/HID）")

            while not detached_event.is_set():
                time.sleep(1)
            try:
                session.detach()
            except Exception:
                pass
            time.sleep(2)
        except Exception as e:
            _log_sync("error", "Frida 异常: " + str(e))
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
        print("缺少 DGHUB_PORT 或 DGHUB_TOKEN")
        return
    uri = f"ws://{host}:{port}/ws/plugin?token={token}"
    async with websockets.connect(uri) as websocket:
        ws = websocket
        await ws.send(json.dumps({
            "op": "hello",
            "token": token,
            "manifest": {
                "id": "rumble_shock",
                "name": "手柄震动映射",
                "version": "1.7.2",
                "sdk": "1",
            },
        }))
        ack = json.loads(await ws.recv())
        if not ack.get("accepted"):
            print("握手失败:", ack)
            return
        await send_log("info", "插件已连接")
        frida_started = False
        async for msg in ws:
            try:
                data = json.loads(msg)
            except Exception:
                continue
            op = data.get("op")
            if op == "stop":
                break
            elif op == "config":
                config.update(data.get("data", {}))
                await send_log("info", "收到全量配置")
                if not frida_started:
                    frida_started = True
                    threading.Thread(target=start_frida, daemon=True).start()
            elif op == "config_changed":
                key, value = data.get("key"), data.get("value")
                if key in config:
                    config[key] = value
                    await send_log("info", f"配置更新: {key}={value}")
            elif op == "device_info":
                device_connected = bool(data.get("connected", False))
                await send_log("info", "设备已连接" if device_connected else "设备未连接")
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