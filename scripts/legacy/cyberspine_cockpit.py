"""
CyberSpine 桌面原生 WinUI 驾驶舱主程序入口 (CyberSpine Desktop Cockpit Main Entry)
"""
import sys
from pathlib import Path

# 确保路径解析
workspace_dir = Path(__file__).resolve().parent
if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))

from src.app.cockpit_app import launch_cockpit_app

if __name__ == '__main__':
    launch_cockpit_app()
