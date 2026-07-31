import pytest
import hashlib
from karyx.security.audit_logger import (
    AuditLogger,
    HashedSha256,
    verify_audit_integrity,
)


def _h(seed):
    """Helper so existing tests don't repeat hex formatting."""
    return HashedSha256(hashlib.sha256(seed.encode()).hexdigest())


def test_audit_logger_chaining():
    logger = AuditLogger(session_id="TEST_SESS")
    h1, h2, h3 = _h("h1"), _h("h2"), _h("h3")
    logger.log_transformation(
        "op1", {"in": h1}, {"out": h2}, {"m": 1}
    )
    logger.log_transformation(
        "op2", {"in": h2}, {"out": h3}, {"m": 2}
    )

    package = logger.finalize_audit_log()
    # entries[0] is the prepended license_verification entry; op1/op2 follow.
    user_entries = [e for e in package["entries"] if e["operation"] in ("op1", "op2")]
    assert len(user_entries) == 2
    assert (
        user_entries[1]["previous_hash"]
        == user_entries[0]["entry_hash"]
    )

    v_result = verify_audit_integrity(package)
    assert v_result["valid"] is True


def test_audit_logger_tampering():
    logger = AuditLogger(session_id="TAMPER_TEST")
    logger.log_transformation(
        "op1", {"in": _h("h1")}, {"out": _h("h2")}, {}
    )
    package = logger.finalize_audit_log()

    op1 = next(e for e in package["entries"] if e["operation"] == "op1")
    op1["operation"] = "tampered_op"

    v_result = verify_audit_integrity(package)
    assert v_result["valid"] is False
    assert "TAMPERING_DETECTED" in v_result["error"]


def test_audit_logger_chain_break():
    logger = AuditLogger(session_id="BREAK_TEST")
    logger.log_transformation(
        "op1", {"in": _h("h1")}, {"out": _h("h2")}, {}
    )
    logger.log_transformation(
        "op2", {"in": _h("h2")}, {"out": _h("h3")}, {}
    )
    package = logger.finalize_audit_log()

    op2 = next(e for e in package["entries"] if e["operation"] == "op2")
    op2["previous_hash"] = "0" * 64

    v_result = verify_audit_integrity(package)
    assert v_result["valid"] is False
    assert "CHAIN_TAMPERING" in v_result["error"] or "FINAL_HASH_MISMATCH" in v_result["error"]
