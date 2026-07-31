# Open-Core Relicense — Karyx

## Goal
Convert Karyx from a single MIT license to a **dual-license / open-core** model:
- **MIT (free forever):** core optimization, quantization, hardware backends, basic
  optimize/verify CLI, and the MCP server (`mcp_karyx`).
- **Karyx Commercial License v1.0:** the military-grade security surface — IL5/IL6
  classified audit trails + air-gap packaging + the `deploy` command.

Intent (owner, pxlcrtiv): **no third party may sell or commercially redistribute the
hardened security features.** Owner retains the right to sell commercial licenses.

## Grounded reality (verified against repo, 2026-07-27)
Existing modules that form the "commercial" surface (all real, all used by the pipeline):
- `karyx/security/audit_logger.py` — hash-chained audit (classification = security_level)
- `karyx/packaging/air_gap_packager.py` — air-gap tarball + manifest
- `karyx/cli/commands/deploy.py` — deployment stub
- `karyx/cli/dashboard.py` — monitoring script

Modules referenced by the original spec that **DO NOT EXIST** and must NOT be invented:
- `karyx/security/stig_compliance.py`
- `karyx/security/signer.py`
- `karyx/adapters/hive.py`  (Hive integration = `mcp_karyx`, kept MIT/open)

## Key constraint (from spec Requirements + Success Criteria — authoritative)
`OptimizationPipeline.run()` calls `AuditLogger` + `create_air_gap_package` for **every**
security level, including free IL4. Therefore:
- **DO NOT** gate `audit_logger.py` / `air_gap_packager.py` at import or `__init__`.
- Gate **only at the command layer**:
  - `optimize.py`: if `--security-level` ∈ {IL5, IL6} and no valid license → emit eval
    warning OR gracefully downgrade to IL4 (do NOT crash). IL4 path stays un-gated.
  - `deploy.py`: `check_license("Secure hardware deployment")` at entry.

## Deliverables
1. `karyx/licensing/__init__.py` — `LicenseManager`, `LicenseError`,
   `get_license_manager()`, `check_license()`. Eval tracking written to
   `~/.karyx/.first_use`; first-use path injectable via constructor for tests.
2. `LICENSE` (dual-license summary), `LICENSE-MIT` (MIT text), `LICENSE-COMMERCIAL`
   (v1.0, contact `vdnhhwvzy7@privaterelay.appleid.com`).
3. `optimize.py` — IL5/IL6 license gate + graceful IL4 downgrade.
4. `deploy.py` — `check_license` at entry.
5. `README.md` License section — dual-license + pricing.
6. `.karyx-license-example.key` — example key + instructions.
7. `.gitignore` — add `.karyx/`, `*.key`.
8. `tests/test_licensing.py` — 8 cases from spec; all 40 existing tests must still pass.

## Out of scope (explicitly)
STIG compliance, HSM signer, Hive adapter as a "premium" module — not in repo; not created.
