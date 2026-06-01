import importlib
import concurrent.futures
import traceback
import time
import pathlib
from typing import Any
from logger import log

_log = log("executor")

# Modules available inside every tool's execution namespace
_ALLOWED_MODULES = [
    "json", "re", "math", "random", "hashlib", "base64",
    "datetime", "uuid", "urllib.parse", "collections",
]

def _build_namespace() -> dict:
    ns: dict = {}
    for mod in _ALLOWED_MODULES:
        try:
            alias = mod.split(".")[-1]
            ns[alias] = importlib.import_module(mod)
        except ImportError:
            pass
    import requests          # required — listed in requirements.txt
    ns["requests"] = requests

    import os, pathlib, subprocess, shutil, glob
    ns["os"] = os
    ns["pathlib"] = pathlib
    ns["subprocess"] = subprocess
    ns["shutil"] = shutil
    ns["glob"] = glob

    # Restricted builtins — no eval/compile/import
    ns["__builtins__"] = {
        "print": print, "len": len, "range": range, "enumerate": enumerate,
        "zip": zip, "map": map, "filter": filter, "sorted": sorted,
        "str": str, "int": int, "float": float, "bool": bool,
        "list": list, "dict": dict, "tuple": tuple, "set": set,
        "isinstance": isinstance, "issubclass": issubclass,
        "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
        "repr": repr, "type": type, "hasattr": hasattr, "getattr": getattr,
        "setattr": setattr, "vars": vars, "dir": dir,
        "Exception": Exception, "ValueError": ValueError,
        "KeyError": KeyError, "TypeError": TypeError,
        "IOError": IOError, "OSError": OSError, "FileNotFoundError": FileNotFoundError,
        "open": open,
        "True": True, "False": False, "None": None,
    }
    return ns


def _resolve_code(tool_def: dict, tool_name: str) -> str | None:
    """
    Resolve tool implementation from one of three sources:
      1. source_file — read Python code from a file on disk
      2. code        — inline Python string stored in the registry
      3. source_url  — HTTP delegate (returns a wrapper that POSTs to the URL)
    Returns the Python source string, or None if nothing found.
    """
    source_file = (tool_def.get("source_file") or "").strip()
    source_url  = (tool_def.get("source_url")  or "").strip()
    inline_code = (tool_def.get("code")        or "").strip()

    if source_file:
        p = pathlib.Path(source_file).expanduser().resolve()
        if not p.exists():
            _log.error("source_file not found: %s", p)
            return None
        code = p.read_text(encoding="utf-8")
        _log.info("TOOL_SOURCE  tool=%s  from=file  path=%s", tool_name, p)
        return code

    if source_url:
        # Generate a wrapper function that POSTs params to the external URL
        code = (
            f"def {tool_name}(**kwargs) -> str:\n"
            f"    import json as _json\n"
            f"    r = requests.post({source_url!r}, json=kwargs, timeout=30)\n"
            f"    r.raise_for_status()\n"
            f"    data = r.json()\n"
            f"    return str(data.get('result', data))\n"
        )
        _log.info("TOOL_SOURCE  tool=%s  from=url  url=%s", tool_name, source_url)
        return code

    if inline_code:
        return inline_code

    return None


def load_tool_fn(tool_def_or_code, tool_name: str):
    """
    Accept either a dict (full tool_def with source_file/source_url/code)
    or a plain code string for backwards compatibility.
    Returns the callable, or None on error.
    """
    if isinstance(tool_def_or_code, str):
        code = tool_def_or_code
    else:
        code = _resolve_code(tool_def_or_code, tool_name)

    if not code:
        return None

    ns = _build_namespace()
    try:
        exec(compile(code, f"<tool:{tool_name}>", "exec"), ns)
        fn = ns.get(tool_name)
        return fn if callable(fn) else None
    except Exception as e:
        _log.error("load_tool_fn failed for '%s': %s", tool_name, e)
        return None


def execute_tool(tool_def_or_code, tool_name: str, params: dict, timeout: int = 30) -> Any:
    """
    Execute a tool. Accepts either a tool_def dict or a plain code string.
    """
    if isinstance(tool_def_or_code, str):
        code = tool_def_or_code
    else:
        code = _resolve_code(tool_def_or_code, tool_name)

    if not code:
        raise ValueError(f"Tool '{tool_name}' has no implementation (no code, source_file, or source_url)")

    ns = _build_namespace()
    try:
        exec(compile(code, f"<tool:{tool_name}>", "exec"), ns)
    except SyntaxError as e:
        _log.error("Syntax error in tool '%s': %s", tool_name, e)
        raise ValueError(f"Syntax error in tool code: {e}")

    fn = ns.get(tool_name)
    if not fn or not callable(fn):
        raise ValueError(f"Function '{tool_name}' not found. Name must match tool name.")

    _log.info("TOOL_CALL  tool=%s  params=%s", tool_name, list(params.keys()))
    t0 = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn, **params)
        try:
            result = future.result(timeout=timeout)
            elapsed = round((time.monotonic() - t0) * 1000)
            preview = str(result)[:120].replace("\n", "↵")
            _log.info("TOOL_OK  tool=%s  ms=%d  result=%r", tool_name, elapsed, preview)
            return result
        except concurrent.futures.TimeoutError:
            elapsed = round((time.monotonic() - t0) * 1000)
            _log.error("TOOL_TIMEOUT  tool=%s  ms=%d", tool_name, elapsed)
            raise TimeoutError(f"Tool '{tool_name}' timed out after {timeout}s")
        except Exception as e:
            elapsed = round((time.monotonic() - t0) * 1000)
            _log.error("TOOL_ERROR  tool=%s  ms=%d  error=%s", tool_name, elapsed, traceback.format_exc().splitlines()[-1])
            raise RuntimeError(f"Tool execution error: {traceback.format_exc()}")
