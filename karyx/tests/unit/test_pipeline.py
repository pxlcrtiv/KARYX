"""Tests for the optimization-pipeline module.

The pipeline owns the orchestration: load → detect → quantize →
optimize → package. The CLI is, after Ticket 2, a thin arg-parsing
shell that calls OptimizationPipeline.run(OptimizationRequest) and
prints the returned ArtifactBundle.
"""
import re
import uuid
from pathlib import Path

import onnx
import pytest
from click.testing import CliRunner
from onnx import helper, TensorProto

from karyx.pipeline import (
    ArtifactBundle,
    OptimizationPipeline,
    OptimizationRequest,
)


def _write_model(path: Path) -> Path:
    X = helper.make_tensor_value_info("X", TensorProto.FLOAT, [1, 1])
    Y = helper.make_tensor_value_info("Y", TensorProto.FLOAT, [1, 1])
    graph = helper.make_graph([helper.make_node("Relu", ["X"], ["Y"])], "t2", [X], [Y])
    onnx.save(helper.make_model(graph), str(path))
    return path


def test_optimization_request_has_uuid_session_id_by_default(tmp_path):
    """Two default requests get different session ids."""
    a = OptimizationRequest(model_path=tmp_path / "a.onnx", target="jetson-nano")
    b = OptimizationRequest(model_path=tmp_path / "b.onnx", target="jetson-nano")
    assert a.session_id != b.session_id
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        a.session_id,
    )


def test_optimization_request_session_id_is_injectable(tmp_path):
    req = OptimizationRequest(
        model_path=tmp_path / "a.onnx",
        target="jetson-nano",
        session_id="INJECTED",
    )
    assert req.session_id == "INJECTED"


def test_pipeline_returns_artifact_bundle(tmp_path, monkeypatch):
    """Pipeline.run() returns an ArtifactBundle with the three
    required fields. Today the impl writes artifacts to cwd; we
    pin cwd to tmp_path.
    """
    model = _write_model(tmp_path / "model.onnx")
    monkeypatch.chdir(tmp_path)
    # Use a session_id we can pass through to the auditor so we can
    # verify the chain end-to-end.
    req = OptimizationRequest(
        model_path=model,
        target="jetson-nano",
        session_id="T2_TEST",
        precision="INT8",
    )
    bundle = OptimizationPipeline().run(req)
    assert isinstance(bundle, ArtifactBundle)
    assert bundle.session_id == "T2_TEST"
    assert Path(bundle.package_path).exists()
    assert bundle.audit_hash


@pytest.fixture
def pinned_cwd(tmp_path, monkeypatch):
    """Pin working directory for the duration of the test."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_pipeline_loads_model_exactly_for_one_pass(pinned_cwd):
    """The pipeline calls ``detect_architecture`` once; the same model
    graph is reused downstream by ``adaptive_quantize`` rather than
    re-loading. Both functions take ``str(model_path)`` today, so
    what's actually asserted is: ``detect_architecture`` opens the
    model only once per pipeline run.
    """
    from karyx import pipeline as pipeline_mod

    opened_count = {"n": 0}
    real_detect = pipeline_mod.detect_architecture

    def detect(model_path):
        opened_count["n"] += 1
        return real_detect(model_path)

    mp = __import__("pytest").MonkeyPatch()
    mp.setattr(pipeline_mod, "detect_architecture", detect)

    try:
        from pathlib import Path
        import onnx
        from onnx import helper, TensorProto

        model_path = pinned_cwd / "model.onnx"
        X = helper.make_tensor_value_info("X", TensorProto.FLOAT, [1, 1])
        Y = helper.make_tensor_value_info("Y", TensorProto.FLOAT, [1, 1])
        graph = helper.make_graph(
            [helper.make_node("Relu", ["X"], ["Y"])], "t2", [X], [Y]
        )
        onnx.save(helper.make_model(graph), str(model_path))

        req = OptimizationRequest(model_path=model_path, target="jetson-nano")
        OptimizationPipeline().run(req)
    finally:
        mp.undo()

    assert opened_count["n"] == 1, (
        f"detect_architecture was called {opened_count['n']} times; "
        f"the pipeline should call it once per run."
    )


def test_pipeline_session_id_round_trips_into_audit_log(pinned_cwd):
    """The session id the pipeline reports in the bundle matches the
    chain's session id, which matches the audit log header.
    """
    import json
    import tarfile

    model = _write_model(pinned_cwd / "model.onnx")
    req = OptimizationRequest(
        model_path=model,
        target="jetson-nano",
        session_id="ROUNDTRIP_TEST",
    )
    bundle = OptimizationPipeline().run(req)
    with tarfile.open(bundle.package_path) as tar:
        audit = json.load(tar.extractfile("security/audit_log.json"))
    assert audit["header"]["session_id"] == "ROUNDTRIP_TEST"
    assert bundle.audit_hash == audit["header"]["final_chain_hash"]



def test_pipeline_no_longer_uses_session_123(tmp_path, monkeypatch):
    """The hard-coded 'SESSION_123' placeholder must be gone."""
    model = _write_model(tmp_path / "model.onnx")
    monkeypatch.chdir(tmp_path)
    req = OptimizationRequest(model_path=model, target="jetson-nano")
    bundle = OptimizationPipeline().run(req)
    assert bundle.session_id != "SESSION_123"


def test_cli_optimize_becomes_thin_shell(tmp_path, monkeypatch):
    """The Click command is a thin shell: it declares options, performs the
    license gate, and delegates to OptimizationPipeline().run(). It must not
    contain pipeline-stage logic (no audit hashing, no packaging, no quantizer
    calls) inline.
    """
    import ast
    from karyx.cli.commands import optimize as opt_module

    tree = ast.parse(Path(opt_module.__file__).read_text())

    # Collect the set of called names anywhere in the module.
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else
        node.func.id if isinstance(node.func, ast.Name) else None
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    called.discard(None)

    forbidden = {
        "adaptive_quantize",
        "optimize_for_hardware",
        "detect_architecture",
        "validate_model",
        "create_air_gap_package",
        "finalize_audit_log",
        "log_transformation",
    }
    leaked = forbidden & called
    assert not leaked, f"optimize.py leaked pipeline logic: {leaked}"

    # And it must delegate to the pipeline.
    assert "OptimizationPipeline" in called, "optimize.py must delegate to OptimizationPipeline"


def test_quantization_step_writes_real_file(tmp_path):
    """The quantizer is supposed to materialize a real file at the
    returned path. Before T2.3 it only renamed the path string.
    The pipeline depends on the file being there.
    """
    model = _write_model(tmp_path / "model.onnx")
    from karyx.quantization.adaptive_quant import adaptive_quantize

    result = adaptive_quantize(str(model), None, "INT8")
    assert Path(result["quantized_model_path"]).exists()
