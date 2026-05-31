import importlib
import concurrent.futures
import traceback
from typing import Any

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
    try:
        import requests
        ns["requests"] = requests
    except ImportError:
        pass

    # Restricted builtins — no file/exec/eval/import
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
        "True": True, "False": False, "None": None,
    }
    return ns


def execute_tool(code: str, tool_name: str, params: dict, timeout: int = 30) -> Any:
    """
    Execute a tool's Python code in a restricted namespace.
    The code must define a function whose name matches tool_name.
    """
    ns = _build_namespace()

    try:
        exec(compile(code, f"<tool:{tool_name}>", "exec"), ns)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in tool code: {e}")

    fn = ns.get(tool_name)
    if not fn or not callable(fn):
        raise ValueError(
            f"Function '{tool_name}' not found in tool code. "
            "Make sure the function name matches the tool name."
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn, **params)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Tool '{tool_name}' timed out after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Tool execution error: {traceback.format_exc()}")


def load_tool_fn(code: str, tool_name: str):
    """Compile tool code and return the callable, or None on error."""
    ns = _build_namespace()
    try:
        exec(compile(code, f"<tool:{tool_name}>", "exec"), ns)
        fn = ns.get(tool_name)
        return fn if callable(fn) else None
    except Exception:
        return None
