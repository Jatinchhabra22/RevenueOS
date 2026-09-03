from fastapi import Depends

from app.services.runtime import AppRuntime

_RUNTIME: AppRuntime | None = None


def get_runtime() -> AppRuntime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = AppRuntime.from_settings()
    return _RUNTIME


def reset_runtime() -> None:
    global _RUNTIME
    _RUNTIME = None


RuntimeDep = Depends(get_runtime)
