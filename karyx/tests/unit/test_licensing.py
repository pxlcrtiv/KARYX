"""Tests for the open-core license manager.

These run without any license file present and use an injectable first-use
path so they never touch the real home directory.
"""

import importlib
import os
from pathlib import Path

import pytest

from karyx.licensing import (
    LicenseManager,
    LicenseError,
    get_license_manager,
    check_license,
)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Ensure a clean license environment for every test."""
    monkeypatch.delenv("KARYX_LICENSE_KEY", raising=False)
    # Point LicenseManager at a throwaway first-use file.
    state = {"path": tmp_path / ".first_use"}

    def make(first_use_path=None):
        return LicenseManager(first_use_path=first_use_path or state["path"])

    # Patch the module-level singleton factory so tests use isolated managers.
    import karyx.licensing as L

    L._manager = None
    L.LicenseManager = make  # type: ignore[assignment]
    # get_license_manager rebuilds using the patched class
    yield state
    L.LicenseManager = LicenseManager  # restore


def test_core_open_without_license():
    """IL4 / core features require no license (Requirement #1)."""
    mgr = LicenseManager(first_use_path=Path("/nonexistent/first_use"))
    # validate_license with no key + no first-use => evaluation (valid)
    status = mgr.validate_license()
    assert status["valid"] is True


def test_il4_no_key_works(tmp_path):
    mgr = LicenseManager(first_use_path=tmp_path / "fu")
    status = mgr.validate_license()
    assert status["mode"] in ("evaluation", "licensed")
    assert status["valid"] is True


def test_il5_triggers_evaluation(tmp_path):
    """Fresh machine, no key, IL5 requested => evaluation window."""
    mgr = LicenseManager(first_use_path=tmp_path / "fu")
    assert mgr.is_evaluation_period_active() is True
    assert mgr.get_evaluation_days_remaining() == 30


def test_evaluation_tracked(tmp_path):
    mgr = LicenseManager(first_use_path=tmp_path / "fu")
    mgr.validate_license()  # records first use
    assert mgr._first_use_time is not None
    assert mgr.get_evaluation_days_remaining() == 30


def test_expired_blocks_commercial(tmp_path):
    fu = tmp_path / "fu"
    fu.write_text("0.0")  # epoch => long expired
    mgr = LicenseManager(first_use_path=fu)
    assert mgr.is_evaluation_period_active() is False
    with pytest.raises(LicenseError):
        mgr.require_license_or_eval("Secure hardware deployment")


def test_valid_key_enables(tmp_path, monkeypatch):
    monkeypatch.setenv("KARYX_LICENSE_KEY", "KARYX-TEST-DEMO-1234")
    mgr = LicenseManager(first_use_path=tmp_path / "fu")
    status = mgr.validate_license()
    assert status["valid"] is True
    assert status["mode"] == "licensed"


def test_key_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("KARYX_LICENSE_KEY", "KARYX-ENV-KEY-XXXX")
    mgr = LicenseManager(first_use_path=tmp_path / "fu")
    assert mgr._find_license_key() == "KARYX-ENV-KEY-XXXX"


def test_key_from_file(tmp_path, monkeypatch):
    monkeypatch.delenv("KARYX_LICENSE_KEY", raising=False)
    keyfile = tmp_path / "license.key"
    keyfile.write_text("KARYX-FILE-KEY-XXXX")
    mgr = LicenseManager(first_use_path=tmp_path / "fu")
    # point file discovery at our temp file
    mgr.license_file_paths = [str(keyfile)]
    assert mgr._find_license_key() == "KARYX-FILE-KEY-XXXX"


def test_check_license_returns_status(tmp_path):
    mgr = LicenseManager(first_use_path=tmp_path / "fu")
    status = check_license("IL5 cryptographic audit trails")
    assert status["valid"] is True
