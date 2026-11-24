"""Heuristic risk indicators for inert Python source reviews.

Flags are advisory only, not a security scanner or sandbox substitute. Source
may use aliases, metaprogramming, extensions or indirect calls. No execution.
"""
from __future__ import annotations
import ast

HIGH_IMPACT = frozenset({
    "eval", "exec", "compile", "__import__",
    "os.system", "os.popen", "os.remove", "os.unlink", "os.rmdir",
    "subprocess.run", "subprocess.Popen", "subprocess.call",
    "subprocess.check_call", "subprocess.check_output",
    "shutil.rmtree", "shutil.move", "shutil.copytree",
    "pickle.loads", "marshal.loads",
    "ctypes.CDLL", "ctypes.WinDLL",
})
WATCH_IMPORTS = frozenset({
    "subprocess", "socket", "ctypes", "pickle", "marshal", "winreg",
    "requests", "urllib", "http", "httpx",
})


def _full_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _full_name(node.value)
        return parent + "." + node.attr if parent else None
    return None


def inspect_python(source, *, filename="<proposal>"):
    """Return bounded findings from AST without importing or executing source."""
    if not isinstance(source, str):
        raise ValueError("Python source must be text")
    tree = ast.parse(source, filename=filename)
    findings = []
    # Import aliases are heuristic: scope shadowing can change meaning.
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".", 1)[0]] = item.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            for item in node.names:
                if item.name != "*":
                    aliases[item.asname or item.name] = node.module + "." + item.name

    for node in ast.walk(tree):
        label = None
        if isinstance(node, ast.Call):
            name = _full_name(node.func)
            if name:
                pieces = name.split(".", 1)
                name = aliases.get(pieces[0], pieces[0]) + (
                    "." + pieces[1] if len(pieces) > 1 else "")
            if name in HIGH_IMPACT:
                label = "high_impact_call:" + name
            if name and name.endswith((".write_text", ".write_bytes", ".unlink")):
                label = "possible_file_write_or_delete:" + name
            elif (isinstance(node.func, ast.Attribute)
                  and node.func.attr in {"write_text", "write_bytes", "unlink"}):
                # Also handles Path(...).write_text(), where the receiver is
                # a call and not a simple dotted expression.
                label = "possible_file_write_or_delete:." + node.func.attr
            if name == "open":
                # Opening a file isn't inherently a write, but flag explicit
                # modes such as w/a/x/+ for manual review.
                mode = None
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                for keyword in node.keywords:
                    if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                        mode = keyword.value.value
                if isinstance(mode, str) and any(ch in mode for ch in "wax+"):
                    label = "possible_file_write:open"
        elif isinstance(node, ast.Import):
            for item in node.names:
                root = item.name.split(".", 1)[0]
                if root in WATCH_IMPORTS:
                    findings.append({"line": node.lineno, "indicator": "watched_import:" + root})
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root in WATCH_IMPORTS:
                label = "watched_import:" + root
        if label:
            findings.append({"line": getattr(node, "lineno", 0), "indicator": label})
    findings.sort(key=lambda item: (item["line"], item["indicator"]))
    return {"advisory_only": True, "manual_review_required": bool(findings),
            "indicators": findings[:40], "indicators_truncated": len(findings) > 40}
