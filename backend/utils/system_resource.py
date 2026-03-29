"""
系统资源探测与动态并发配置
"""
from __future__ import annotations

import ctypes
import os
import platform
from typing import Dict, Tuple


def _get_available_memory_gb() -> float:
    """
    获取可用物理内存（GB）
    优先使用 psutil，缺失时在 Windows 使用 WinAPI，最后回退到保守值。
    """
    try:
        import psutil  # type: ignore

        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        pass

    if platform.system().lower() == "windows":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullAvailPhys / (1024 ** 3)

    # 最终回退：按 2GB 可用内存估算
    return 2.0


def calculate_dynamic_workers(
    total_files: int,
    *,
    min_workers: int = 1,
    max_workers: int = 5,
) -> Tuple[int, Dict[str, float]]:
    """
    根据当前系统资源动态计算推荐并发 worker 数量。

    规则：
    - CPU 约束：IO密集场景默认使用 2x CPU
    - 内存约束：每个并发按约 0.6GB 预留
    - 文件数约束：并发不超过待处理文件总数
    """
    cpu_count = max(1, os.cpu_count() or 1)
    available_memory_gb = max(0.5, _get_available_memory_gb())

    cpu_based = cpu_count * 2
    memory_based = max(1, int(available_memory_gb / 0.6))
    file_based = max(1, total_files)

    workers = min(cpu_based, memory_based, file_based, max_workers)
    workers = max(min_workers, workers)

    detail = {
        "cpu_count": float(cpu_count),
        "available_memory_gb": round(available_memory_gb, 2),
        "cpu_based_workers": float(cpu_based),
        "memory_based_workers": float(memory_based),
        "max_workers": float(max_workers),
        "final_workers": float(workers),
    }
    return workers, detail

