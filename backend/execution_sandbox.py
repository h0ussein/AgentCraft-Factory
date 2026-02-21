# execution_sandbox.py
# Execution Sandbox: run tool code in a restricted environment (RestrictedPython)

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, List

# Optional: RestrictedPython for compile-time and runtime restrictions
try:
    from RestrictedPython import compile_restricted_exec
    from RestrictedPython.Guards import (
        safe_builtins,
        full_write_guard,
        guarded_iter_unpack_sequence,
    )
    _restricted_available = True
except ImportError:
    compile_restricted_exec = None
    guarded_iter_unpack_sequence = None
    _restricted_available = False

import json as _json
import requests as _requests
import math as _math
import re as _re
import datetime as _datetime
from decimal import Decimal as _Decimal


def _safe_import(name: str, globals=None, locals=None, fromlist=(), level=0):
    """Allow only safe stdlib/API modules: json, requests, math, re, datetime, decimal."""
    _allowed = {
        "json": _json,
        "requests": _requests,
        "math": _math,
        "re": _re,
        "datetime": _datetime,
        "decimal": __import__("decimal"),
    }
    if name in _allowed:
        return _allowed[name]
    raise ImportError(f"Import of '{name}' is not allowed in the tool sandbox.")


def _fallback_safe_builtins():
    """When RestrictedPython is not installed, use a subset of builtins (no open, eval, exec, etc.)."""
    import builtins
    allowed = {
        "None", "True", "False", "bool", "int", "float", "str", "list", "dict", "tuple",
        "set", "range", "len", "min", "max", "sum", "abs", "round", "sorted", "reversed",
        "enumerate", "zip", "map", "filter", "iter", "next", "isinstance", "type", "callable",
        "getattr", "setattr", "hasattr", "repr", "print", "Exception", "ValueError", "TypeError",
        "KeyError", "IndexError", "AttributeError", "RuntimeError", "KeyError", "slice",
        "ord", "chr", "divmod", "pow", "all", "any", "format", "id", "hash", "issubclass",
    }
    return {k: getattr(builtins, k) for k in allowed if hasattr(builtins, k)}


def _build_sandbox_globals():
    """Build the restricted globals dict: safe builtins + json, requests, math, re, datetime, decimal, os.getenv."""
    safe_os = SimpleNamespace(getenv=os.getenv)
    g = {
        "__builtins__": safe_builtins if _restricted_available else _fallback_safe_builtins(),
        "__name__": "tool_sandbox",
        "__metaclass__": type,
        "json": _json,
        "requests": _requests,
        "math": _math,
        "re": _re,
        "datetime": _datetime,
        "Decimal": _Decimal,
        "os": safe_os,
        "__import__": _safe_import,
    }
    if _restricted_available:
        g["_write_"] = full_write_guard
        g["_getattr_"] = getattr
        g["_getiter_"] = iter
        g["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence
    return g


def run_restricted_source(source_code: str, filename: str = "<tool>") -> dict:
    """
    Compile and execute source code in a restricted environment.
    Returns the globals dict after execution (so callers can extract functions).
    """
    if _restricted_available and compile_restricted_exec:
        result = compile_restricted_exec(source_code, filename=filename)
        if result.errors:
            raise SyntaxError(f"RestrictedPython compilation failed: {result.errors}")
        globs = _build_sandbox_globals()
        exec(result.code, globs)
        return globs
    # Fallback: execute with limited globals (no RestrictedPython)
    globs = _build_sandbox_globals()
    exec(compile(source_code, filename, "exec"), globs)
    return globs


def load_tool_functions_from_source(
    source_code: str,
    filename: str,
    custom_tools_dir: Path,
    file_path_resolved: Path,
) -> List[Callable]:
    """
    Execute tool source in the sandbox and return only callable functions defined in it.
    Ensures the code is considered to be from custom_tools (file_path_resolved must be under custom_tools_dir).
    """
    try:
        file_path_resolved = Path(file_path_resolved).resolve()
        custom_tools_dir = Path(custom_tools_dir).resolve()
        file_path_resolved.relative_to(custom_tools_dir)
    except (ValueError, Exception):
        return []

    globs = run_restricted_source(source_code, filename=str(file_path_resolved))
    funcs = []
    for name, obj in globs.items():
        if name.startswith("_"):
            continue
        if callable(obj) and hasattr(obj, "__doc__") and not isinstance(obj, type):
            funcs.append(obj)
    return funcs


def is_sandbox_available() -> bool:
    """Return True if RestrictedPython is available for stricter sandboxing."""
    return _restricted_available
