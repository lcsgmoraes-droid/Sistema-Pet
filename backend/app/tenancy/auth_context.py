from contextvars import ContextVar

_auth_mode: ContextVar[bool] = ContextVar("auth_mode", default=False)

def enable_auth_mode():
    _auth_mode.set(True)

def disable_auth_mode():
    _auth_mode.set(False)

def is_auth_mode() -> bool:
    return _auth_mode.get()