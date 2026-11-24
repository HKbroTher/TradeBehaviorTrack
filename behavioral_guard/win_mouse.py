"""Windows-only cursor polling adapter. It never reads keyboard key codes or text."""

import ctypes
import os
from ctypes import wintypes


class Point(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class GuiThreadInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND), ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND), ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND), ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


class WindowsMouse:
    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("Windows mouse adapter requires Windows")
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(Point)]
        self.user32.GetCursorPos.restype = wintypes.BOOL
        self.user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
        self.user32.GetAsyncKeyState.restype = ctypes.c_short
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetGUIThreadInfo.argtypes = [wintypes.DWORD, ctypes.POINTER(GuiThreadInfo)]
        self.user32.GetGUIThreadInfo.restype = wintypes.BOOL
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetClassNameW.restype = ctypes.c_int
        self.user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.GetWindowLongW.restype = wintypes.LONG
        self.kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel32.OpenProcess.restype = wintypes.HANDLE
        self.kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def foreground_exe(self) -> str | None:
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        handle = self.kernel32.OpenProcess(0x1000, False, pid.value)
        if not handle:
            return None
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if not self.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                return None
            return os.path.basename(buffer.value).lower()
        finally:
            self.kernel32.CloseHandle(handle)

    def sensitive_focus(self) -> bool:
        """Exclude classic password edits; unknown focus state fails closed."""
        info = GuiThreadInfo()
        info.cbSize = ctypes.sizeof(info)
        if not self.user32.GetGUIThreadInfo(0, ctypes.byref(info)):
            return True
        if not info.hwndFocus:
            return True
        name = ctypes.create_unicode_buffer(256)
        if not self.user32.GetClassNameW(info.hwndFocus, name, len(name)):
            return True
        if name.value.lower() == "edit":
            return bool(self.user32.GetWindowLongW(info.hwndFocus, -16) & 0x20)
        return False

    def sample(self) -> tuple[int, int, bool]:
        point = Point()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            raise OSError(ctypes.get_last_error(), "GetCursorPos failed")
        return point.x, point.y, bool(self.user32.GetAsyncKeyState(0x01) & 0x8000)
