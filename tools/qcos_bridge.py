"""ctypes door into libsaem: JSON in, JSON out, never throws."""
import ctypes, json, pathlib, functools

ROOT = pathlib.Path(__file__).resolve().parents[1]

@functools.lru_cache(maxsize=1)
def _lib():
    for cand in (ROOT/"core"/"build"/"libsaem.so", ROOT/"build"/"libsaem.so",
                 ROOT/"core"/"build"/"libsaem.dylib"):
        if cand.exists():
            lib = ctypes.CDLL(str(cand))
            lib.saem_call.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            lib.saem_call.restype = ctypes.c_char_p
            lib.saem_methods.argtypes = []
            lib.saem_methods.restype = ctypes.c_char_p
            return lib
    return None

def available(): return _lib() is not None

def call_raw(method, args_json="{}"):
    lib = _lib()
    if lib is None: return json.dumps({"ok": False, "error": "libsaem not built"})
    return lib.saem_call(method.encode(), args_json.encode()).decode()

def call(method, **args):
    return json.loads(call_raw(method, json.dumps(args, separators=(",", ":"))))

def methods():
    lib = _lib()
    return json.loads(lib.saem_methods().decode()) if lib else []
