# Spec: `mcp-karyx` — MCP server wrapping Karyx

## Goal
Expose Karyx's model-hardening pipeline as a set of **Model Context Protocol (MCP)** tools so a Hive agent (or any MCP client) can harden + verify edge AI models as a verifiable, auditable tool.

This is the idiomatic Hive integration (Hive connects business systems as tools via MCP). Each Karyx call produces a **tamper-evident air-gap package with a hash-chained audit log** — turning a Hive agent's non-deterministic output into a provable artifact.

## API surface (from `karyx.pipeline` / CLI)
- `OptimizationPipeline().run(OptimizationRequest(...))` -> `ArtifactBundle(session_id, package_path, audit_hash)`
- `verify_audit_integrity(audit_log, artifact_map?)` -> `{"valid": bool, "error"?: str, "operations_verified"?: int}`
- `deploy` is a **stub** today (`--package`, `--target-host`, prints only).

## Tools (MCP)
1. `karyx_optimize`
   - params: `model: str` (path), `target: str` (jetson-nano|jetson-xavier|xilinx-zynq|generic-arm), `precision?: str` (default INT8), `security_level?: str` (default IL4)
   - returns: `{package_path, audit_hash, session_id}`
2. `karyx_verify`
   - params: `package: str` (path to .tar.gz)
   - returns: `{valid: bool, operations_verified?: int, error?: str, final_chain_hash?: str}`
3. `karyx_deploy`
   - params: `package: str`, `target_host?: str`
   - returns: `{deployed: bool, message: str}` (delegates to stub; marks itself as not-yet-implemented)

## Deliverables
- `mcp_karyx/` package: server entry (`server.py`) using the `mcp` Python SDK (`FastMCP`), tool definitions in `tools.py`, thin wrapper over `karyx` API in `wrapper.py`.
- `pyproject.toml` additions: `[project.optional-dependencies] mcp = ["mcp"]` and a `mcp-karyx` console script.
- `.mcp.json` at repo root documenting how Hive consumes it (stdio server command).
- Tests (`mcp_karyx/tests/`) mocking `karyx.pipeline.OptimizationPipeline` and `verify_audit_integrity` — TDD: red first, then green.
- `README.md` section: "Using Karyx as an MCP server (Hive integration)".
- One end-to-end smoke test: run `mcp-karyx` against `test_model.onnx`, confirm it produces a valid package + hash.

## Non-goals
- Do NOT implement real deployment logic (deploy remains a transparent stub).
- Do NOT modify Karyx core; only wrap it.

## Conventions
- Follow Karyx's vocabulary: module, interface, seam, adapter.
- Tests must not be no-ops: mock the pipeline so a regression in the wrapper fails the test.
