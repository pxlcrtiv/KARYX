# KARYX

Military-grade edge AI model optimization and deployment suite.

`karyx` takes a validated ONNX model, detects its architecture family, quantizes it for a target precision, ships it through an air-gap package, and produces a tamper-evident audit log of every transformation.

> Status: **milestones 1–4 complete** (engine, security, multi-hardware, workflows, test suite).

## Quickstart

```bash
git clone https://github.com/pxlcrtiv/KARYX.git
cd KARYX
python3 -m venv .venv
source .venv/bin/activate
pip install onnx networkx numpy click PyYAML cryptography pytest
karyx optimize --help
```

The CLI entry point is `karyx.cli.main:main` (see `pyproject.toml`'s `[project.scripts]`). It's a tiny Click group with three subcommands.

## The pipeline

```
validate  →  detect_architecture  →  adaptive_quantize  →  optimize_for_hardware  →  audit_log  →  air_gap_package
```

| Stage | Module | What it does |
|---|---|---|
| **validate** | `karyx.core.validator` | Checks the model exists, has size > 0, has a recognized extension. |
| **detect architecture** | `karyx.core.arch_detector` | Parses the ONNX graph with NetworkX, walks Conv/Add/Attention nodes, classifies the model family. |
| **adaptive quantize** | `karyx.quantization.adaptive_quant` | Picks a precision per layer based on the arch profile. |
| **optimize for hardware** | `karyx.hardware.optimizer_factory` | Dispatches to the right backend. |
| **audit log** | `karyx.security.audit_logger` | Hash-chained journaling of every input and output. |
| **air-gap package** | `karyx.packaging.air_gap_packager` | Tarballs the model + runtime + manifest + audit log. |

## Supported targets

| Target string | Backend |
|---|---|
| `jetson-nano`, `jetson-xavier`, `jetson-orin` | `TensorRTOptimizer` (`karyx/hardware/tensorrt_optimizer.py`) |
| `xilinx-*` (e.g. `xilinx-zynq`) | `VitisAIOptimizer` (`karyx/hardware/vitis_optimizer.py`) |
| `generic-arm` | `ONNXOptimizer` (`karyx/hardware/onnx_optimizer.py`) |

Routing is done by string-prefix match in `optimize_for_hardware`. Run `auto_detect_hardware()` to inspect the host.

## Security levels

Each optimization run is parameterized with a classification. The audit logger stamps the chain with it. The packager emits a `manifest.json` carrying the classification and the air-gap filename uses the classification suffix (`.il4.tar.gz`, `.il5.tar.gz`, `.il6.tar.gz`).

## CLI

```
karyx optimize --help
karyx verify  --help
karyx deploy  --help
```

- `optimize` runs the full pipeline and writes a package to disk.
- `verify` reads a package's audit log and confirms its chain integrity.
- `deploy` is a stub today (see `karyx/cli/commands/deploy.py`).

A dashboard script lives at `karyx/cli/dashboard.py` for visualizing a run.

## Workflows

The repo ships iFlow workflow specs at `karyx/workflows/iflow/`. `optimize.yaml` and `deploy.yaml` describe the steps each CLI command should execute. **The YAMLs are aspirational in places** — see the architecture review for the seven keys that currently disagree between spec and code.

## Development

```bash
pytest            # 12 tests, ~0.2s on a modern laptop
```

Tests cover the audit chain, architecture detection, quantization plan selection, packaging, and a CLI smoke test.

### Project layout

```
karyx/
├── cli/                 # Click entry points + dashboard
│   ├── main.py
│   ├── dashboard.py
│   └── commands/
│       ├── optimize.py
│       ├── verify.py
│       └── deploy.py
├── core/                # validation, arch detection, model loading
├── hardware/            # ABC + factory + three backends
├── quantization/        # adaptive per-layer precision
├── security/            # hash-chained audit logging
├── packaging/           # air-gap tarball + manifest
├── utils/               # cross-cutting helpers
├── workflows/iflow/     # YAML workflow specs
└── tests/
    ├── unit/
    ├── integration/
    └── security/

generate_mock_model.py    # CLI helper to write a fake ONNX model
pyproject.toml            # build config + entry point
```

## Conventions

- **Vocabulary.** Module, interface, depth, seam, adapter, leverage, locality — used consistently across plans and reviews.
- **Deletable tests.** If a test could only "pass against itself", rewrite the production code so the test cannot be a no-op.
- **No secrets in code.** `.env*` is gitignored; signing keys never live in the repo.

## License

MIT — see [LICENSE](LICENSE).
