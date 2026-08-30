"""
CyberSpine AIDA64 后台守护进程自动发现与静默托管器 (AIDA64 Companion Daemon Manager)
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional


class Aida64DaemonManager:
    """AIDA64 后台守护进程管理器"""

    CANDIDATE_PATHS = [
        Path(__file__).resolve().parent.parent.parent.parent / "vendor" / "aida64" / "aida64.exe",
        Path(r"C:\Program Files (x86)\FinalWire\AIDA64 Extreme\aida64.exe"),
        Path(r"C:\Program Files\FinalWire\AIDA64 Extreme\aida64.exe"),
        Path(r"C:\Program Files (x86)\FinalWire\AIDA64 Engineer\aida64.exe"),
        Path(r"C:\Program Files\FinalWire\AIDA64 Engineer\aida64.exe"),
        Path(r"D:\AIDA64\aida64.exe"),
        Path(r"E:\AIDA64\aida64.exe"),
    ]

    _process: Optional[subprocess.Popen] = None

    @classmethod
    def is_shared_memory_active(cls) -> bool:
        """快速探测 AIDA64_SensorValues 共享内存是否处于活动更新状态"""
        if sys.platform != "win32":
            return False
        try:
            import mmap
            shm = mmap.mmap(-1, 0x10000, "AIDA64_SensorValues", access=mmap.ACCESS_READ)
            data = shm.read(256)
            shm.close()
            return len(data.strip(b'\x00')) > 0
        except Exception:
            return False

    @classmethod
    def find_executable(cls) -> Optional[Path]:
        """寻找可用的 aida64.exe 可执行文件"""
        for path in cls.CANDIDATE_PATHS:
            if path.exists() and path.is_file():
                return path
        return None

    @classmethod
    def auto_start_if_available(cls) -> bool:
        """若已激活共享内存则直接复用；若未激活但存在 aida64.exe 则静默在后台拉起"""
        if cls.is_shared_memory_active():
            return True

        exe_path = cls.find_executable()
        if not exe_path:
            return False

        try:
            sys.stderr.write(f"[AIDA64-Daemon] 发现便携版/安装版 AIDA64: {exe_path}，正在静默后台拉起...\n")
            sys.stderr.flush()
            cls._process = subprocess.Popen(
                [str(exe_path), "/SILENT", "/MIN"],
                cwd=str(exe_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )

            # 等待 1.5 秒让共享内存映射完成
            for _ in range(6):
                time.sleep(0.3)
                if cls.is_shared_memory_active():
                    sys.stderr.write("[AIDA64-Daemon] AIDA64 共享内存挂载成功！\n")
                    sys.stderr.flush()
                    return True
            return False
        except Exception as e:
            sys.stderr.write(f"[AIDA64-Daemon] 启动异常: {e}\n")
            sys.stderr.flush()
            return False
