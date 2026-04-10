"""
Integration tests for DataFlow WebUI.
Run: python test_integration.py
"""
import sys
import httpx

BASE = "http://127.0.0.1:8000"
passed = 0
failed = 0

def test(label, fn):
    global passed, failed
    try:
        result = fn()
        print(f"  PASS  {label}")
        if result is not None:
            print(f"        {result}")
        passed += 1
    except Exception as e:
        print(f"  FAIL  {label}")
        print(f"        {str(e)[:120]}")
        failed += 1


print("=" * 55)
print("  DataFlow WebUI Integration Tests")
print("=" * 55)

print("\n--- Core API ---")
test(
    "[1] Operators count",
    lambda: f"{len(httpx.get(BASE + '/api/v1/operators/', timeout=5).json().get('data', []))} operators available",
)
test(
    "[2] Datasets endpoint",
    lambda: f"HTTP {httpx.get(BASE + '/api/v1/datasets/', timeout=5).status_code}",
)
test(
    "[3] Pipelines endpoint",
    lambda: f"HTTP {httpx.get(BASE + '/api/v1/pipelines/', timeout=5).status_code}",
)

print("\n--- MCP Server (import check) ---")
test(
    "[8] MCP server importable",
    lambda: __import__("mcp") and "mcp imported OK",
)

test(
    "[9] MCP server script syntax",
    lambda: (
        compile(
            open("C:/Users/zhenh/OneDrive/Desktop/projects/DataFlow-Skills/mcp-server/server.py",
                 encoding="utf-8").read(),
            "server.py",
            "exec",
        )
        and "server.py syntax OK"
    ),
)

print("\n--- Cursor Skills (local file check) ---")
import os
from pathlib import Path

cursor_skills = Path.home() / ".cursor" / "skills"
test(
    "[10] dataflow-pipeline-generator skill installed",
    lambda: f"SKILL.md found ({(cursor_skills / 'dataflow-pipeline-generator' / 'SKILL.md').stat().st_size} bytes)",
)
test(
    "[11] dataflow-webui skill installed",
    lambda: f"SKILL.md found ({(cursor_skills / 'dataflow-webui' / 'SKILL.md').stat().st_size} bytes)",
)
test(
    "[12] generate.py script accessible",
    lambda: f"exists ({(cursor_skills / 'dataflow-pipeline-generator' / 'scripts' / 'generate.py').stat().st_size} bytes)",
)
test(
    "[13] webui.py script accessible",
    lambda: f"exists ({(cursor_skills / 'dataflow-webui' / 'scripts' / 'webui.py').stat().st_size} bytes)",
)

print("\n--- MCP Config in Cursor settings ---")
import json
settings_path = Path(os.environ.get("APPDATA", "")) / "Cursor" / "User" / "settings.json"
test(
    "[14] MCP server registered in Cursor settings.json",
    lambda: (
        lambda cfg: f"dataflow-webui MCP: command={cfg['mcp']['servers']['dataflow-webui']['command']}"
    )(json.loads(settings_path.read_text(encoding="utf-8"))),
)

print("\n" + "=" * 55)
print(f"  Results: {passed} passed, {failed} failed")
print("=" * 55)
sys.exit(0 if failed == 0 else 1)
