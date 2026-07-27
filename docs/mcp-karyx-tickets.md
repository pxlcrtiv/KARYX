# Tickets: `mcp-karyx`

Blocking order (work blockers-first):

- [ ] **T1 — Scaffold `mcp_karyx` package + transport** (`blocks: T2,T3`)
  Create `mcp_karyx/` with `server.py` (FastMCP stdio server), `wrapper.py` (thin import shim over `karyx`), `tools.py` (placeholder tool registration), `pyproject.toml` optional `mcp` extra + `mcp-karyx` script, and `mcp_karyx/tests/`. Server must start and register zero-or-more tools without crashing.

- [ ] **T2 — Implement `karyx_optimize` tool** (`blocks: T4`)
  Wire `karyx_optimize` to `OptimizationPipeline().run`. Returns package_path/audit_hash/session_id. Add TDD test mocking the pipeline to assert the tool surfaces those fields and propagates validation errors.

- [ ] **T3 — Implement `karyx_verify` + `karyx_deploy` tools** (`blocks: T4`)
  `karyx_verify` reads the package, extracts `security/audit_log.json`, calls `verify_audit_integrity`, returns validity + chain hash. `karyx_deploy` wraps the stub with a clear "not yet implemented" boolean. TDD tests for both.

- [ ] **T4 — Wiring doc + `.mcp.json` + E2E smoke** (`blocks: none`)
  Add `.mcp.json` (stdio command `mcp-karyx`), README section, and a runnable smoke that optimizes `test_model.onnx` and verifies the resulting package via the MCP tools. Confirm `python -m pytest` green and server boots.

## Definition of done
- `pytest` green for `mcp_karyx/tests/`
- `mcp-karyx` console script boots a stdio MCP server
- `.mcp.json` present and consumable by Hive
- README documents the Hive integration
