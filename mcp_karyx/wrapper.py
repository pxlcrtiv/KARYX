"""Thin adapter over the karyx public API.

Every function here is a pure delegation — no business logic, no
side effects beyond what karyx already owns.  The wrapper exists so
the MCP tool layer never imports karyx internals directly; swapping
the underlying implementation is a one-file edit.
"""
from pathlib import Path
from typing import Any, Dict, Optional

from karyx.pipeline import OptimizationPipeline, OptimizationRequest, ArtifactBundle
from karyx.security.audit_logger import verify_audit_integrity, PathRef


def optimize(
    model: str,
    target: str,
    precision: str = "INT8",
    security_level: str = "IL4",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run the full optimization pipeline and return bundle metadata."""
    kwargs: Dict[str, Any] = {
        "model_path": Path(model),
        "target": target,
        "precision": precision,
        "security_level": security_level,
    }
    if session_id:
        kwargs["session_id"] = session_id

    req = OptimizationRequest(**kwargs)
    bundle: ArtifactBundle = OptimizationPipeline().run(req)
    return {
        "package_path": bundle.package_path,
        "audit_hash": bundle.audit_hash,
        "session_id": bundle.session_id,
    }


def verify(package: str) -> Dict[str, Any]:
    """Extract audit_log from the package and verify its chain integrity."""
    import json
    import tarfile

    try:
        with tarfile.open(package, "r:gz") as tar:
            audit_file = tar.extractfile("security/audit_log.json")
            if audit_file is None:
                return {"valid": False, "error": "security/audit_log.json missing from package"}
            audit_log = json.load(audit_file)
    except KeyError:
        return {"valid": False, "error": "security/audit_log.json missing from package"}
    except FileNotFoundError:
        return {"valid": False, "error": f"package not found: {package}"}

    return verify_audit_integrity(audit_log)


def deploy(package: str, target_host: Optional[str] = None) -> Dict[str, Any]:
    """Stub — real deployment is not yet implemented."""
    return {
        "deployed": False,
        "message": f"Deploy stub: would deploy {package}"
        + (f" to {target_host}" if target_host else ""),
    }
