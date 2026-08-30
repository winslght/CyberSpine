"""
CyberSpine 原生 WinUI 桌面应用程序宿主 (Cockpit App Host)
使用 Microsoft Edge WebView2 渲染 100% 原生 Fluent Design 3.0 亚克力驾驶舱界面。
"""
import os
import sys
import time
import socket
import threading
import subprocess
from pathlib import Path

# 确保导入路径
current_dir = Path(__file__).resolve().parent
core_dir = current_dir.parent.parent
if str(core_dir) not in sys.path:
    sys.path.insert(0, str(core_dir))

from src.app.app_bridge import CyberSpineAppBridge


def _is_ollama_alive(host: str = "127.0.0.1", port: int = 11434) -> bool:
    """快速 TCP 探测 Ollama 是否在监听"""
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except Exception:
        return False


def _auto_start_ollama() -> bool:
    """若 Ollama 未运行则自动后台拉起，最多等 10 秒"""
    if _is_ollama_alive():
        print("[CyberSpine] Ollama already running on port 11434.")
        return True

    # 查找 ollama 可执行文件
    ollama_candidates = [
        r"C:\Users\winslght\AppData\Local\Programs\Ollama\ollama.exe",
        "ollama",
    ]
    ollama_exe = None
    for candidate in ollama_candidates:
        if candidate == "ollama":
            import shutil
            if shutil.which("ollama"):
                ollama_exe = "ollama"
                break
        elif Path(candidate).exists():
            ollama_exe = candidate
            break

    if not ollama_exe:
        print("[CyberSpine] WARNING: Ollama executable not found. Model will use heuristic fallback.")
        return False

    print(f"[CyberSpine] Auto-starting Ollama on NVIDIA RTX 4060 GPU: {ollama_exe} serve")
    try:
        env = os.environ.copy()
        cuda_dir = Path(ollama_exe).parent / "lib" / "ollama" / "cuda_v12"
        sys32 = r"C:\Windows\System32"
        env["PATH"] = f"{cuda_dir};{sys32};" + env.get("PATH", "")
        env["CUDA_VISIBLE_DEVICES"] = "0"
        env["OLLAMA_FLASH_ATTENTION"] = "1"
        env["OLLAMA_NUM_PARALLEL"] = "1"

        subprocess.Popen(
            [ollama_exe, "serve"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
    except Exception as e:
        print(f"[CyberSpine] Failed to start Ollama: {e}")
        return False

    # 最多等 10 秒让 Ollama 就绪
    print("[CyberSpine] Waiting for Ollama to start (up to 10s)...", end="", flush=True)
    for i in range(20):
        time.sleep(0.5)
        if _is_ollama_alive():
            print(f" ready in {(i+1)*0.5:.1f}s")
            return True
        print(".", end="", flush=True)
    print(" timeout, continuing anyway")
    return False



def launch_cockpit_app():
    """启动 CyberSpine 原生 WinUI 桌面应用"""
    ui_dir = core_dir / "src" / "ui"
    index_html = ui_dir / "index.html"

    if not index_html.exists():
        print(f"[ERROR] UI resource not found: {index_html}")
        return

    # Step 1: 自动探测并拉起 Ollama 服务（RTX 4060 GPU 神经网络引擎）
    print("[CyberSpine] Step 1/3: Checking Ollama GPU engine...")
    _auto_start_ollama()

    # Step 2: 重置起搏器单例，确保每次 App 启动都能正确初始化物理起搏线程
    print("[CyberSpine] Step 2/3: Initializing pacemaker daemon...")
    from src.pacing.real_pacemaker import RealAutonomousPacemaker
    with RealAutonomousPacemaker._singleton_lock:
        if RealAutonomousPacemaker._instance is not None:
            try:
                RealAutonomousPacemaker._instance.stop()
            except Exception:
                pass
        RealAutonomousPacemaker._instance = None

    # Step 3: 创建桥接层（内部自动创建并启动起搏器守护线程）
    bridge = CyberSpineAppBridge()

    # 确认起搏器线程已在运行
    if not bridge.pacemaker._is_running:
        bridge.pacemaker.start()

    print(f"[CyberSpine] Step 3/3: Pacemaker running: {bridge.pacemaker._is_running}, interval: {bridge.pacemaker.interval_seconds}s")
    print(f"[CyberSpine] Heartbeat log: {bridge.pacemaker.ticks_log_file}")

    try:
        import webview
        print("[CyberSpine] Launching WinUI 3 Cockpit window...")

        # 创建原生 WinUI 窗口
        window = webview.create_window(
            title="🧬 CyberSpine Neural Cockpit - 神经中枢驾驶舱",
            url=str(index_html),
            js_api=bridge,
            width=1120,
            height=740,
            min_size=(960, 620),
            background_color='#18191c',
            text_select=False,
            easy_drag=True,
        )

        # 启动 WebView2 原生 GUI 循环（主线程阻塞，pacemaker daemon 线程在后台持续跳动）
        webview.start(debug=False)

    except ImportError:
        print("⚠️ 未安装 pywebview，正在以轻量原生浏览器模式预览...")
        import webbrowser
        webbrowser.open(index_html.as_uri())
        # 浏览器预览时让主线程保持运行以维持起搏器线程
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    launch_cockpit_app()
