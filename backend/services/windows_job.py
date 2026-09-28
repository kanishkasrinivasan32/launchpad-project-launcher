"""Windows jobs keep npm/cmd descendants owned even after their parent exits."""
import ctypes
import os
from ctypes import wintypes


class WindowsJob:
    def __init__(self, pid):
        self.handle = None
        if os.name != 'nt':
            return
        self.api = ctypes.WinDLL('kernel32', use_last_error=True)
        api = self.api
        api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        api.CreateJobObjectW.restype = wintypes.HANDLE
        api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        api.OpenProcess.restype = wintypes.HANDLE
        api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        api.QueryInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p]
        api.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        api.CloseHandle.argtypes = [wintypes.HANDLE]

        class BasicLimit(ctypes.Structure):
            _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64),
                        ('flags', wintypes.DWORD), ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t),
                        ('active', wintypes.DWORD), ('affinity', ctypes.c_size_t),
                        ('priority', wintypes.DWORD), ('scheduling', wintypes.DWORD)]

        class ExtendedLimit(ctypes.Structure):
            _fields_ = [('basic', BasicLimit), ('io', ctypes.c_uint64 * 6),
                        ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t),
                        ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]

        self.handle = api.CreateJobObjectW(None, None)
        limits = ExtendedLimit()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        process = api.OpenProcess(0x0100 | 0x0001, False, pid)
        try:
            if not self.handle or not process or not api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not api.AssignProcessToJobObject(self.handle, process):
                raise OSError(ctypes.get_last_error(), 'Could not attach the project to a Windows process job.')
        except Exception:
            self.close()
            raise
        finally:
            if process:
                api.CloseHandle(process)

    def pids(self):
        if not self.handle:
            return []
        for capacity in (256, 4096, 65536):
            class PidList(ctypes.Structure):
                _fields_ = [('assigned', wintypes.DWORD), ('count', wintypes.DWORD), ('ids', ctypes.c_size_t * capacity)]
            result = PidList()
            if self.api.QueryInformationJobObject(self.handle, 3, ctypes.byref(result), ctypes.sizeof(result), None):
                return list(result.ids[:result.count])
            if ctypes.get_last_error() != 234:
                raise OSError(ctypes.get_last_error(), 'Could not read the Windows process job.')
        raise OSError('Too many project processes to monitor.')

    def close(self):
        if self.handle:
            self.api.TerminateJobObject(self.handle, 1)
            self.api.CloseHandle(self.handle)
            self.handle = None
