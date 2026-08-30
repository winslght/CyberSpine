"""
CyberSpine 神经末梢: 瞬时工作记忆与剪贴板语义感知探针 (Clipboard Semantics Perceptor)
毫秒级嗅探剪贴板内容类型（代码、JSON、URL、文件路径、普通文本），捕捉用户正在交换的信息特征。
【安全脱敏】：仅分析模式特征与字符长度，截断摘要脱敏，杜绝私密信息泄露。
"""
import sys
import time
import ctypes
import hashlib
from typing import Dict, Any, List, Optional
from ctypes import c_void_p, c_uint, c_wchar_p

from src.models.somatic_signals import RawSomaticSignal, utc_now
from src.perceptors.base import BasePerceptor


class ClipboardSemanticsPerceptor(BasePerceptor):
    """瞬时工作记忆剪贴板语义嗅探感知器"""

    PERCEPTOR_ID = "nerve.system.clipboard_semantics"
    CHANNEL = "CLIPBOARD_SEMANTICS"

    def __init__(self):
        super().__init__(perceptor_id=self.PERCEPTOR_ID, channel=self.CHANNEL)
        self._last_content_hash: str = ""
        self._last_semantics: Dict[str, Any] = {
            "perceptor_id": self.perceptor_id,
            "content_type": "EMPTY",
            "length": 0,
            "line_count": 0,
            "preview": "",
            "has_content": False,
        }

        # 预先配置 Windows 64 位 ctypes 签名，防止内存访问越界
        if sys.platform == "win32":
            try:
                self._user32 = ctypes.windll.user32
                self._kernel32 = ctypes.windll.kernel32
                self._user32.OpenClipboard.argtypes = [c_void_p]
                self._user32.GetClipboardData.restype = c_void_p
                self._user32.GetClipboardData.argtypes = [c_uint]
                self._kernel32.GlobalLock.restype = c_void_p
                self._kernel32.GlobalLock.argtypes = [c_void_p]
                self._kernel32.GlobalUnlock.argtypes = [c_void_p]
            except Exception:
                pass

    def _get_clipboard_text(self) -> Optional[str]:
        """安全读取当前 Windows 剪贴板文本内容 (严格 64 位指针安全)"""
        if sys.platform != "win32":
            return None

        CF_UNICODETEXT = 13
        try:
            if not self._user32.OpenClipboard(None):
                return None
        except Exception:
            return None

        text = None
        try:
            h_data = self._user32.GetClipboardData(CF_UNICODETEXT)
            if h_data:
                p_data = self._kernel32.GlobalLock(h_data)
                if p_data:
                    try:
                        text = c_wchar_p(p_data).value
                    finally:
                        self._kernel32.GlobalUnlock(h_data)
        except Exception:
            pass
        finally:
            try:
                self._user32.CloseClipboard()
            except Exception:
                pass

        return text

    def _classify_text_pattern(self, text: str) -> str:
        """浅层识别文本模式"""
        trimmed = text.strip()
        if not trimmed:
            return "EMPTY"

        # URL 链接
        if trimmed.startswith(("http://", "https://", "ftp://")):
            return "URL_LINK"

        # 文件路径
        if (len(trimmed) > 2 and trimmed[1:3] in (":\\", ":/")) or trimmed.startswith(("\\\\", "/")):
            return "FILE_PATH"

        # JSON 数据
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
            if ":" in trimmed:
                return "JSON_DATA"

        # 代码特征模式
        code_keywords = ["def ", "class ", "import ", "from ", "function ", "const ", "let ", "var ", "SELECT ", "public static", "int main"]
        if any(kw in trimmed for kw in code_keywords) or ("{" in trimmed and "}" in trimmed and ";" in trimmed):
            return "SOURCE_CODE"

        # 报错堆栈
        if any(err in trimmed for err in ["Traceback (most recent call last)", "Error:", "Exception:", "at line "]):
            return "ERROR_STACK_TRACE"

        return "GENERAL_TEXT"

    def get_baseline(self) -> Dict[str, Any]:
        """获取当前剪贴板语义基线快照"""
        raw_text = self._get_clipboard_text() or ""
        text_hash = hashlib.md5(raw_text.encode('utf-8', errors='ignore')).hexdigest()

        if text_hash != self._last_content_hash:
            self._last_content_hash = text_hash
            pattern = self._classify_text_pattern(raw_text)
            lines = raw_text.splitlines()

            # 脱敏预览 (前 40 字符)
            preview = raw_text.replace("\n", " ").strip()[:40]
            if len(raw_text) > 40:
                preview += "..."

            self._last_semantics = {
                "perceptor_id": self.perceptor_id,
                "content_type": pattern,
                "length": len(raw_text),
                "line_count": len(lines),
                "preview": preview,
                "has_content": len(raw_text) > 0,
            }

        return self._last_semantics

    def poll_signals(self) -> List[RawSomaticSignal]:
        """轮询剪贴板更新事件"""
        start_time = time.perf_counter()
        signals: List[RawSomaticSignal] = []

        now = utc_now()
        raw_text = self._get_clipboard_text() or ""
        text_hash = hashlib.md5(raw_text.encode('utf-8', errors='ignore')).hexdigest()

        if raw_text and text_hash != self._last_content_hash:
            self.get_baseline()
            sig = RawSomaticSignal(
                signal_id=f"sig_clip_{int(now.timestamp() * 1000)}",
                timestamp=now,
                channel=self.channel,
                event_type="CLIPBOARD_UPDATED",
                source_probe=self.perceptor_id,
            )
            signals.append(sig)

        self.record_poll_metric((time.perf_counter() - start_time) * 1000)
        return signals
