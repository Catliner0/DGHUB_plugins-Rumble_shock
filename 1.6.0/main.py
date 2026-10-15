import asyncio
import json
import os
import time
import threading
import frida
import websockets

# ====================== 默认配置 ======================
config = {
    "min_rumble": 800,
    "cooldown": 0.45,
    "duration": 0.65,
    "strength_scale": 75,
    "min_level": 20,
    "max_level": 95,
    "use_max_motor": True,
    "channel": "both",
    "strength_mode": "rollback",
    "action": "both",
    "preset": "CS2-受伤",
    "process_name": "OuterWilds.exe",
    "process_mode": "manual",  # manual / auto
}

ws = None
loop = None
last_time = 0
last_time_lock = threading.Lock()
device_connected = True

# 自动扫描时排除的常见非游戏进程
EXCLUDE_PROCESSES = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe", "explorer.exe",
    "taskhostw.exe", "sihost.exe", "runtimebroker.exe", "searchhost.exe",
    "startmenuexperiencehost.exe", "shellhost.exe", "applicationframehost.exe",
    "conhost.exe", "cmd.exe", "powershell.exe", "pwsh.exe",
    "python.exe", "pythonw.exe", "py.exe",
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "iexplore.exe",
    "discord.exe", "telegram.exe", "wechat.exe", "qq.exe",
    "steam.exe", "steamwebhelper.exe", "steamclient.exe",
    "code.exe", "devenv.exe", "notepad.exe", "notepad++.exe",
    "taskmgr.exe", "procmon.exe", "procmon64.exe",
}


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

        mode = "回落" if config.get("strength_mode") == "rollback" else "永久叠加"
        msg = "触发电击 +" + str(level) + "% | 通道:" + str(config.get("channel")) + " | 模式:" + mode
        await send_log("info", msg)
        print("[" + time.strftime("%H:%M:%S") + "] " + msg)
    except Exception as e:
        await send_log("error", "发送失败: " + str(e))
        print("发送失败: " + str(e))


def on_message(message, data):
    global last_time

    if message.get("type") != "send":
        return

    payload = message.get("payload") or {}
    left = int(payload.get("left", 0))
    right = int(payload.get("right", 0))

    if config.get("use_max_motor", True):
        intensity = max(left, right)
    else:
        intensity = (left + right) // 2

    if intensity < int(config.get("min_rumble", 800)):
        return

    with last_time_lock:
        now = time.time()
        if now - last_time < float(config.get("cooldown", 0.45)):
            return
        last_time = now

    raw_level = int(intensity / 65535.0 * float(config.get("strength_scale", 75)))
    min_level = int(config.get("min_level", 20))
    max_level = int(config.get("max_level", 95))
    level = max(min_level, min(max_level, raw_level))

    if loop and loop.is_running():
        log_msg = "检测到震动 左=" + str(left) + " 右=" + str(right) + " -> 强度" + str(level) + "%"
        asyncio.run_coroutine_threadsafe(send_log("info", log_msg), loop)
        asyncio.run_coroutine_threadsafe(trigger_shock(level), loop)


def _log_sync(level: str, message: str):
    print("[" + time.strftime("%H:%M:%S") + "] " + message)
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(send_log(level, message), loop)


def _report_status_sync(text: str):
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(report_status(text), loop)


def scan_for_xinput_processes():
    """只扫描并返回加载了 XInput 的进程列表，不自动附加"""
    candidates = []
    try:
        try:
            device = frida.get_local_device()
            processes = device.enumerate_processes()
        except Exception:
            processes = frida.enumerate_processes()
    except Exception as e:
        _log_sync("error", "枚举进程失败: " + str(e))
        return candidates

    total = len(processes)
    _log_sync("info", f"开始扫描进程（共 {total} 个）...")

    checked = 0
    for proc in processes:
        name = proc.name
        name_lower = name.lower()
        checked += 1

        if checked % 20 == 0:
            _log_sync("info", f"扫描进度: {checked}/{total}")

        if name_lower in EXCLUDE_PROCESSES:
            continue
        if not name_lower.endswith(".exe"):
            continue
        if any(x in name_lower for x in ["helper", "service", "update", "crash", "report", "cef", "gpu"]):
            continue

        try:
            session = frida.attach(proc.pid)
            try:
                modules = session.enumerate_modules()
                has_xinput = any("xinput" in m.name.lower() for m in modules)
                if has_xinput:
                    candidates.append((name, proc.pid))
                    _log_sync("info", f"发现候选: {name}  (PID {proc.pid})")
            finally:
                try:
                    session.detach()
                except Exception:
                    pass
        except Exception:
            continue

    return candidates


def start_frida():
    """启动 Frida 监听（支持重试 + 自动扫描仅列出候选）"""
    while True:
        session = None
        mode = config.get("process_mode", "manual").lower()

        try:
            if mode == "auto":
                _log_sync("info", "进程模式: 自动扫描（仅列出候选，不自动附加）")
                _report_status_sync("自动扫描中（仅列出）...")

                candidates = scan_for_xinput_processes()

                if not candidates:
                    _log_sync("warning", "未找到加载 XInput 的进程")
                    _log_sync("info", "8 秒后重新扫描...")
                    _report_status_sync("未找到候选进程，重试中")
                    time.sleep(8)
                    continue

                _log_sync("info", "=" * 50)
                _log_sync("info", f"扫描完成，共找到 {len(candidates)} 个候选进程：")
                for i, (name, pid) in enumerate(candidates, 1):
                    _log_sync("info", f"  {i}. {name}   (PID: {pid})")
                _log_sync("info", "=" * 50)
                _log_sync("info", "请将正确的进程名复制到【手动模式】的进程名配置中，然后切换到手动模式并重启插件")
                _report_status_sync(f"找到 {len(candidates)} 个候选，请切换手动模式")

                time.sleep(12)
                continue

            else:
                # 手动模式
                process_name = config.get("process_name", "OuterWilds.exe")
                _log_sync("info", "进程模式: 手动 | 目标: " + process_name)
                _report_status_sync("正在查找 " + process_name)

                try:
                    session = frida.attach(process_name)
                except Exception as e:
                    _log_sync("error", "附加失败: " + str(e) + "，5 秒后重试")
                    _report_status_sync("进程未找到，重试中")
                    time.sleep(5)
                    continue

                _log_sync("info", "Frida 已成功附加到目标进程")
                _report_status_sync("已附加，正在监听")

                detached_event = threading.Event()

                def on_detached(reason):
                    _log_sync("warning", "进程已脱离: " + str(reason) + "，准备重新搜索")
                    detached_event.set()

                session.on("detached", on_detached)

                script = session.create_script("""
                function tryHook(name) {
                    const mod = Process.findModuleByName(name);
                    if (!mod) return false;
                    let addr = null;
                    try {
                        addr = mod.findExportByName("XInputSetState") || mod.getExportByName("XInputSetState");
                    } catch (e) {}
                    if (!addr) return false;
                    console.log("[+] Hooked " + name);
                    Interceptor.attach(addr, {
                        onEnter(args) {
                            try {
                                const vib = args[1];
                                if (vib.isNull()) return;
                                send({left: vib.readU16(), right: vib.add(2).readU16()});
                            } catch (e) {}
                        }
                    });
                    return true;
                }

                const versions = ["xinput1_4.dll","xinput1_3.dll","xinput9_1_0.dll","XInput1_4.dll","XInput1_3.dll"];
                let ok = false;
                for (const dll of versions) {
                    if (tryHook(dll)) { ok = true; break; }
                }
                console.log(ok ? "[+] 监听成功" : "[-] 未找到 XInputSetState");
                """)
                script.on("message", on_message)
                script.load()

                _log_sync("info", "Frida 监听已启动，等待手柄震动数据")
                _report_status_sync("正在监听手柄震动")

                while not detached_event.is_set():
                    time.sleep(1)

                try:
                    session.detach()
                except Exception:
                    pass

                _log_sync("info", "开始重新搜索进程...")
                time.sleep(2)

        except Exception as e:
            _log_sync("error", "Frida 运行异常: " + str(e) + "，5 秒后重试")
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
        print("缺少环境变量 DGHUB_PORT 或 DGHUB_TOKEN")
        print("请通过 DGHub 启动本插件")
        return

    uri = "ws://" + str(host) + ":" + str(port) + "/ws/plugin?token=" + str(token)
    print("正在连接 DGHub: " + uri)

    async with websockets.connect(uri) as websocket:
        ws = websocket

        await ws.send(json.dumps({
            "op": "hello",
            "token": token,
            "manifest": {
                "id": "rumble_shock",
                "name": "手柄震动映射",
                "version": "1.6.0",
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
                print("收到停止指令，退出")
                await send_log("info", "收到停止指令，插件退出")
                break

            elif op == "config":
                config.update(data.get("data", {}))
                print("收到全量配置")
                await send_log("info", "收到全量配置")
                mode = config.get("process_mode", "manual")
                await send_log("info", "当前进程模式: " + str(mode))
                if mode == "manual":
                    await send_log("info", "目标进程名: " + str(config.get("process_name", "")))
                if not frida_started:
                    frida_started = True
                    threading.Thread(target=start_frida, daemon=True).start()

            elif op == "config_changed":
                key = data.get("key")
                value = data.get("value")
                if key in config:
                    config[key] = value
                    await send_log("info", "配置已更新: " + str(key) + " = " + str(value))
                    if key in ("process_name", "process_mode"):
                        await send_log("warning", "进程相关配置已修改，请重启插件后生效")
                        await report_status("进程配置已改，请重启插件")

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