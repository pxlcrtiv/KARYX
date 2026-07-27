"""Karyx license manager — open-core gating for commercial features.

Open-source components (core, hardware, quantization, basic CLI, MCP server)
work with no license key and no network call. Commercial components
(IL5/IL6 audit trails, air-gap packaging, deploy) require a valid license
key for production use, and fall back to a 30-day evaluation window.

Design rules (from docs/open-core-license.md):
- NEVER gate audit_logger.py / air_gap_packager.py at import or __init__.
- Gate ONLY at the command layer (see karyx/cli/commands/optimize.py, deploy.py).
- Free IL4 path must run with zero license files and zero network calls.
- Evaluation window is tracked per-machine at ~/.karyx/.first_use and is
  injectable via the constructor for tests.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional

EVALUATION_DAYS = 30
LICENSE_ENV_VAR = "KARYX_LICENSE_KEY"
LICENSE_FILE_PATHS = [
    "~/.karyx/license.key",
    "./.karyx/license.key",
    "/etc/karyx/license.key",
]
_KEY_PREFIX = "KARYX"


class LicenseError(Exception):
    """Raised when a commercial feature is requested without a valid license."""


class LicenseManager:
    """Validates license status for commercial Karyx features.

    Open-source features never call this. Commercial features call
    ``require_license_or_eval`` at their command entry point.
    """

    def __init__(self, first_use_path: Optional[Path] = None) -> None:
        # Injectable so tests don't touch the real home dir.
        self._first_use_path = first_use_path or (
            Path.home() / ".karyx" / ".first_use"
        )
        self.license_file_paths = [p for p in LICENSE_FILE_PATHS]
        self._first_use_time: Optional[float] = self._load_first_use_time()
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_until: float = 0.0

    # --- evaluation window -------------------------------------------------

    def _load_first_use_time(self) -> Optional[float]:
        if self._first_use_path.exists():
            try:
                return float(self._first_use_path.read_text().strip())
            except (ValueError, OSError):
                return None
        # Don't create the file here; only the first status check does,
        # and tests can pre-seed first_use_path. Keep this side-effect-free.
        return None

    def _record_first_use(self) -> float:
        now = time.time()
        try:
            self._first_use_path.parent.mkdir(parents=True, exist_ok=True)
            self._first_use_path.write_text(str(now))
        except OSError:
            pass
        return now

    def is_evaluation_period_active(self) -> bool:
        if self._first_use_time is None:
            return True
        elapsed = (time.time() - self._first_use_time) / 86400.0
        return elapsed <= EVALUATION_DAYS

    def get_evaluation_days_remaining(self) -> int:
        if self._first_use_time is None:
            return EVALUATION_DAYS
        elapsed = (time.time() - self._first_use_time) / 86400.0
        return max(0, EVALUATION_DAYS - int(elapsed))

    # --- key discovery -----------------------------------------------------

    def _find_license_key(self) -> Optional[str]:
        env_key = os.environ.get(LICENSE_ENV_VAR)
        if env_key:
            return env_key.strip()
        for path_str in self.license_file_paths:
            path = Path(path_str).expanduser()
            if path.exists():
                try:
                    return path.read_text().strip()
                except OSError:
                    continue
        return None

    @staticmethod
    def _validate_license_format(key: str) -> bool:
        """Structural check only (no network, no crypto yet).

        Format: KARYX-XXXX-XXXX-XXXX-XXXX. A real deployment would verify an
        RSA signature against a public key; this placeholder preserves the
        open-core UX (key presence + prefix) without phoning home.
        """
        if not key or len(key) < 10:
            return False
        if not key.upper().startswith(_KEY_PREFIX):
            return False
        parts = key.split("-")
        return len(parts) >= 2

    # --- public API --------------------------------------------------------

    def validate_license(self) -> Dict[str, Any]:
        """Return the current license status for commercial features."""
        # 1 hour cache to avoid repeated file reads (Requirement #4).
        if self._cache and time.time() < self._cache_until:
            return self._cache

        key = self._find_license_key()
        if key and self._validate_license_format(key):
            result: Dict[str, Any] = {
                "valid": True,
                "mode": "licensed",
                "days_remaining": -1,
                "message": "Commercial license validated. Full features enabled.",
            }
        elif self.is_evaluation_period_active():
            remaining = self.get_evaluation_days_remaining()
            # First real check records the evaluation start.
            if self._first_use_time is None:
                self._first_use_time = self._record_first_use()
            result = {
                "valid": True,
                "mode": "evaluation",
                "days_remaining": remaining,
                "message": (
                    f"Evaluation mode: {remaining} days remaining. "
                    f"Purchase a license from pxlcrtiv@proton.me"
                ),
            }
        else:
            result = {
                "valid": False,
                "mode": "expired",
                "days_remaining": 0,
                "message": "Evaluation expired. Purchase a license from pxlcrtiv@proton.me",
            }

        self._cache = result
        self._cache_until = time.time() + 3600.0
        return result

    def require_license_or_eval(self, feature_name: str) -> Dict[str, Any]:
        """Gate a commercial feature.

        Returns the status dict on success (so callers can show eval warnings),
        raises ``LicenseError`` only when evaluation has expired AND no key.
        """
        status = self.validate_license()
        if not status["valid"]:
            raise LicenseError(
                f"Feature '{feature_name}' requires a commercial license.\n"
                f"Status: {status['message']}\n"
                f"Get a license: pxlcrtiv@proton.me"
            )
        return status


_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """Return the process-wide license manager (lazy singleton)."""
    global _manager
    if _manager is None:
        _manager = LicenseManager()
    return _manager


def check_license(feature_name: str) -> Dict[str, Any]:
    """Convenience wrapper used by command entry points."""
    return get_license_manager().require_license_or_eval(feature_name)
