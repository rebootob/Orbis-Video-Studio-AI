from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "wp020_live_r2_preflight.py"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "wp020-live-r2-preflight.yml"

FORBIDDEN_PROVIDER_CALLS = {
    "generate_story",
    "generate_image",
    "generate_video",
    "generate_audio",
    "submit_generation",
    "create_task",
}


def test_r2_preflight_script_compiles_and_has_no_provider_generation_calls():
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)

    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert called_attributes.isdisjoint(FORBIDDEN_PROVIDER_CALLS)
    assert "paid_provider_calls" in source
    assert '"paid_provider_calls": 0' in source
    assert '"execution_fence_written": False' in source


def test_r2_preflight_workflow_is_manual_only_and_cannot_write_execution_fence():
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in source
    assert "\n  push:" not in source
    assert "\n  pull_request:" not in source
    assert "issues: write" not in source
    assert "contents: read" in source
    assert "Paid provider calls: 0" in source
    assert "wp020_live_r2_preflight.py" in source
    assert "wp020_live_uat.py" not in source
