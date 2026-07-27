"""TDD tests for mcp_karyx tools.

All tests mock the heavy karyx pipeline so regressions in the
wrapper/tool layer are caught without touching disk artifacts.
"""
import json
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_karyx import wrapper
from mcp_karyx.tools import register_tools
from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# T2: karyx_optimize
# ---------------------------------------------------------------------------

class TestOptimize:
    def test_returns_required_fields(self):
        """wrapper.optimize surfaces package_path, audit_hash, session_id."""
        fake_bundle = MagicMock()
        fake_bundle.package_path = "/tmp/fake.tar.gz"
        fake_bundle.audit_hash = "a" * 64
        fake_bundle.session_id = "sess-1"

        with patch("mcp_karyx.wrapper.OptimizationPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = fake_bundle
            result = wrapper.optimize(
                model="/tmp/model.onnx",
                target="jetson-nano",
                precision="INT8",
                security_level="IL4",
            )

        assert result["package_path"] == "/tmp/fake.tar.gz"
        assert result["audit_hash"] == "a" * 64
        assert result["session_id"] == "sess-1"

    def test_passes_session_id_when_given(self):
        fake_bundle = MagicMock()
        fake_bundle.package_path = "p"
        fake_bundle.audit_hash = "h"
        fake_bundle.session_id = "custom-id"

        with patch("mcp_karyx.wrapper.OptimizationPipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = fake_bundle
            wrapper.optimize(
                model="/m.onnx",
                target="jetson-nano",
                session_id="custom-id",
            )
            req = MockPipeline.return_value.run.call_args[0][0]
            assert req.session_id == "custom-id"

    def test_propagates_validation_error(self):
        with patch("mcp_karyx.wrapper.OptimizationPipeline") as MockPipeline:
            MockPipeline.return_value.run.side_effect = ValueError(
                "model validation failed: file not found"
            )
            with pytest.raises(ValueError, match="model validation failed"):
                wrapper.optimize(model="/bad.onnx", target="jetson-nano")

    def test_tool_registration_on_server(self):
        """karyx_optimize appears as a registered tool name."""
        mcp = FastMCP("test")
        register_tools(mcp)
        names = [t.name for t in mcp._tool_manager.list_tools()]
        assert "karyx_optimize" in names


# ---------------------------------------------------------------------------
# T3: karyx_verify
# ---------------------------------------------------------------------------

class TestVerify:
    def test_returns_valid_true_for_good_package(self, tmp_path):
        """wrapper.verify extracts audit_log and delegates to verify_audit_integrity."""
        from karyx.security.audit_logger import AuditLogger, HashedSha256
        import hashlib

        logger = AuditLogger(session_id="VERIFY_T", classification="IL4")
        h = lambda s: HashedSha256(hashlib.sha256(s.encode()).hexdigest())
        logger.log_transformation("op1", {"in": h("a")}, {"out": h("b")}, {})
        audit_log = logger.finalize_audit_log()

        pkg = tmp_path / "test.tar.gz"
        with tarfile.open(str(pkg), "w:gz") as tar:
            # audit_log
            audit_bytes = json.dumps(audit_log).encode()
            import io
            info = tarfile.TarInfo(name="security/audit_log.json")
            info.size = len(audit_bytes)
            tar.addfile(info, io.BytesIO(audit_bytes))
            # manifest
            manifest = json.dumps({"package_id": "x"}).encode()
            info2 = tarfile.TarInfo(name="manifest.json")
            info2.size = len(manifest)
            tar.addfile(info2, io.BytesIO(manifest))

        result = wrapper.verify(str(pkg))
        assert result["valid"] is True
        assert result["operations_verified"] == 1

    def test_returns_valid_false_for_tampered(self, tmp_path):
        from karyx.security.audit_logger import AuditLogger, HashedSha256
        import hashlib

        logger = AuditLogger(session_id="TAMPER_T", classification="IL4")
        h = lambda s: HashedSha256(hashlib.sha256(s.encode()).hexdigest())
        logger.log_transformation("op1", {"in": h("a")}, {"out": h("b")}, {})
        audit_log = logger.finalize_audit_log()
        # tamper
        audit_log["entries"][0]["operation"] = "TAMPERED"

        pkg = tmp_path / "tamper.tar.gz"
        with tarfile.open(str(pkg), "w:gz") as tar:
            import io
            audit_bytes = json.dumps(audit_log).encode()
            info = tarfile.TarInfo(name="security/audit_log.json")
            info.size = len(audit_bytes)
            tar.addfile(info, io.BytesIO(audit_bytes))

        result = wrapper.verify(str(pkg))
        assert result["valid"] is False
        assert "error" in result

    def test_missing_audit_log_returns_error(self, tmp_path):
        pkg = tmp_path / "empty.tar.gz"
        with tarfile.open(str(pkg), "w:gz") as tar:
            import io
            manifest = json.dumps({"package_id": "x"}).encode()
            info = tarfile.TarInfo(name="manifest.json")
            info.size = len(manifest)
            tar.addfile(info, io.BytesIO(manifest))

        result = wrapper.verify(str(pkg))
        assert result["valid"] is False
        assert "missing" in result["error"]

    def test_tool_registration(self):
        mcp = FastMCP("test")
        register_tools(mcp)
        names = [t.name for t in mcp._tool_manager.list_tools()]
        assert "karyx_verify" in names


# ---------------------------------------------------------------------------
# T3: karyx_deploy (stub)
# ---------------------------------------------------------------------------

class TestDeploy:
    def test_returns_not_deployed(self):
        result = wrapper.deploy("/tmp/pkg.tar.gz", target_host="10.0.0.1")
        assert result["deployed"] is False
        assert "10.0.0.1" in result["message"]

    def test_no_host(self):
        result = wrapper.deploy("/tmp/pkg.tar.gz")
        assert result["deployed"] is False
        assert "stub" in result["message"].lower()

    def test_tool_registration(self):
        mcp = FastMCP("test")
        register_tools(mcp)
        names = [t.name for t in mcp._tool_manager.list_tools()]
        assert "karyx_deploy" in names


# ---------------------------------------------------------------------------
# Server entry-point smoke
# ---------------------------------------------------------------------------

class TestServerSmoke:
    def test_import_server_does_not_crash(self):
        import mcp_karyx.server as srv
        assert hasattr(srv, "mcp")

    def test_three_tools_registered(self):
        import mcp_karyx.server as srv
        names = [t.name for t in srv.mcp._tool_manager.list_tools()]
        assert sorted(names) == ["karyx_deploy", "karyx_optimize", "karyx_verify"]
