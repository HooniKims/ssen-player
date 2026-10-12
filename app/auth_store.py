"""SsenSeries v4 store: same DPAPI entropy, revision and mutex as the auth kit."""
import ctypes
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
import uuid

ENTROPY = b'SsenSeries.Auth.v4'
MUTEX = 'Local\\SsenSeriesAuthV4'

class Blob(ctypes.Structure):
    _fields_ = [('size', wt.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]

def dpapi(data, decrypt=False):
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    fn = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.POINTER(Blob),
                   ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(Blob)]
    fn.restype = wt.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    def blob(raw):
        buf = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        return Blob(len(raw), buf), buf
    source, source_buffer = blob(data)
    entropy, entropy_buffer = blob(ENTROPY)
    target = Blob()
    if not fn(ctypes.byref(source), None, ctypes.byref(entropy), None, None, 1, ctypes.byref(target)):
        raise OSError('DPAPI')
    try: return ctypes.string_at(target.data, target.size)
    finally: kernel.LocalFree(target.data)

class SharedStore:
    def __init__(self, path=None, mutex=MUTEX):
        self.path = Path(path) if path else Path(os.environ['LOCALAPPDATA'])/'SsenSeries/Auth/v4.bin'
        self.mutex = mutex

    def request(self, request):
        if request.get('op') not in ('read', 'write'):
            return {'bridgeError': 'BAD_OPERATION'}
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wt.BOOL, wt.LPCWSTR]
        kernel.CreateMutexW.restype = wt.HANDLE
        kernel.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
        kernel.WaitForSingleObject.restype = wt.DWORD
        kernel.ReleaseMutex.argtypes = [wt.HANDLE]
        kernel.CloseHandle.argtypes = [wt.HANDLE]
        handle = kernel.CreateMutexW(None, False, self.mutex)
        if not handle: return {'bridgeError': 'STORE_ERROR'}
        held = False
        try:
            held = kernel.WaitForSingleObject(handle, 10000) in (0, 0x80)
            if not held: return {'bridgeError': 'STORE_BUSY'}
            current = {'revision': 0, 'state': None}
            if self.path.exists():
                try:
                    if self.path.stat().st_size > 8 * 1024 * 1024: raise ValueError()
                    current = json.loads(dpapi(self.path.read_bytes(), True).decode('utf-8-sig'))
                    if (type(current['revision']) is not int or current['revision'] < 0
                            or not isinstance(current['state'], dict)): raise ValueError()
                except Exception: return {'bridgeError': 'STORE_CORRUPT'}
            if request['op'] == 'read': return current
            if type(request.get('revision')) is not int or request['revision'] != current['revision']:
                return {'bridgeError': 'STORE_CONFLICT'}
            if not isinstance(request.get('state'), dict): return {'bridgeError': 'STORE_CORRUPT'}
            revision = current['revision'] + 1
            raw = json.dumps({'revision': revision, 'state': request['state']}, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            if len(raw) > 1024 * 1024: return {'bridgeError': 'STORE_CORRUPT'}
            encrypted = dpapi(raw)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(self.path.name + '.' + uuid.uuid4().hex + '.tmp')
            try:
                with temporary.open('xb') as file:
                    file.write(encrypted)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, self.path)
            finally: temporary.unlink(missing_ok=True)
            return {'revision': revision}
        except Exception: return {'bridgeError': 'STORE_ERROR'}
        finally:
            if held: kernel.ReleaseMutex(handle)
            kernel.CloseHandle(handle)
