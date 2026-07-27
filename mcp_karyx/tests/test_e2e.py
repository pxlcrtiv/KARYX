"""End-to-end smoke test for mcp-karyx.

Optimises test_model.onnx through the wrapper, then verifies the
resulting package.  This is a real pipeline run (not mocked) so it
catches integration regressions.
"""
import os
from pathlib import Path

import pytest

from mcp_karyx import wrapper

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(
    not (REPO_ROOT / "test_model.onnx").exists(),
    reason="test_model.onnx not present in repo root",
)
def test_optimize_then_verify(tmp_path, monkeypatch):
    """Full round-trip: optimize → package → verify."""
    monkeypatch.chdir(tmp_path)

    result = wrapper.optimize(
        model=str(REPO_ROOT / "test_model.onnx"),
        target="jetson-nano",
        precision="INT8",
        security_level="IL5",
        session_id="E2E-SMOKE",
    )

    assert result["package_path"]
    assert result["audit_hash"]
    assert result["session_id"] == "E2E-SMOKE"
    assert Path(result["package_path"]).exists(), "package file should exist on disk"

    # Verify the package we just built.
    v = wrapper.verify(result["package_path"])
    assert v["valid"] is True, f"verify failed: {v.get('error')}"
    assert v["operations_verified"] >= 1
