# Tickets: Open-Core Relicense

Blocking order:

- [ ] **T1 — Licensing module** (`blocks: T3,T4`) — `karyx/licensing/__init__.py`
  with `LicenseManager` (env + file key discovery, format check, 30-day eval
  tracking, graceful validate), `LicenseError`, `get_license_manager()`,
  `check_license()`. First-use path injectable for tests.
- [ ] **T2 — License files** (`blocks: none`) — `LICENSE` (dual summary),
  `LICENSE-MIT` (reuse existing MIT body), `LICENSE-COMMERCIAL` (v1.0).
- [ ] **T3 — Command gates** (`blocks: T5`) — `optimize.py` IL5/IL6 gate + IL4
  downgrade; `deploy.py` `check_license` at entry. **Do NOT touch
  audit_logger.py / air_gap_packager.py.**
- [ ] **T4 — Docs + gitignore + example key** (`blocks: none`) — README License
  section, `.gitignore` (`.karyx/`, `*.key`), `.karyx-license-example.key`.
- [ ] **T5 — Tests** (`blocks: none`) — `tests/test_licensing.py` (8 cases);
  confirm `pytest -q` → 40 + new all green; IL4 works with `~/.karyx` removed.

## Acceptance (from owner spec)
- `optimize --security-level IL4` with NO license file → works, no license message.
- `optimize --security-level IL5` on fresh machine → "30 days remaining" eval warning, runs.
- `optimize --security-level IL5` after eval expiry → "expired", downgrades to IL4.
- `KARYX_LICENSE_KEY=KARYX-TEST-DEMO-1234` → "Commercial license validated".
- All existing tests still pass.
