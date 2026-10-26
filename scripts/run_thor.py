#!/usr/bin/env python3
"""Run the archived V4 harness on an idle Thor with explicit local paths."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[1]
TASK = REPO / "snapshot"
SOURCE = TASK / "baseline/phyai-official"
REVISION = "75403624f9c8858f347f624e3b032553fa756ac2"
MAIN = ["len31_17", "len65_97", "len128_129", "len257_7"]
SHAPES = ["video320x512", "video17frames", "action16"]


def task_path(value):
    path = Path(value)
    return (path if path.is_absolute() else TASK / path).resolve()


def environment():
    env = os.environ.copy()
    modules = [
        SOURCE / "phyai/src",
        SOURCE / "phyai-kernel",
        SOURCE / "phyai-utils-tools/src",
        SOURCE / "phyai-ext/src",
        TASK / "solution",
        TASK / "bench",
    ]
    env.update(
        COSMOS_TASK_ROOT=str(TASK),
        COSMOS_SOURCE_ROOT=str(SOURCE),
        PYTHONPATH=os.pathsep.join(map(str, modules)),
        CUDA_HOME="/usr/local/cuda-13.0",
        CUTE_DSL_ARCH="sm_110a",
        TRITON_PTXAS_PATH="/usr/local/cuda-13.0/bin/ptxas",
        TRITON_PTXAS_BLACKWELL_PATH="/usr/local/cuda-13.0/bin/ptxas",
        TORCHINDUCTOR_CACHE_DIR=str(TASK / "cache/torchinductor"),
        PHYAI_KERNEL_CACHE_ROOT=str(TASK / "cache/phyai_kernel"),
        TRITON_CACHE_DIR=str(TASK / "cache/triton"),
        CUDA_CACHE_PATH=str(TASK / "cache/cuda"),
    )
    return env


def capture(argv, env):
    return subprocess.check_output(
        argv, env=env, text=True, stderr=subprocess.STDOUT, timeout=30
    ).strip()


def preflight(python, env):
    if platform.machine() != "aarch64":
        raise RuntimeError("GPU execution requires Thor ARM64; use --dry-run here.")
    smi = shutil.which("nvidia-smi") or "/usr/sbin/nvidia-smi"
    gpu = capture([smi, "--query-gpu=name,compute_cap", "--format=csv,noheader"], env)
    if len(gpu.splitlines()) != 1 or "Thor" not in gpu or "11.0" not in gpu:
        raise RuntimeError(f"Expected one Thor SM110 device; observed {gpu!r}")
    processes = capture(
        [
            smi,
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader",
        ],
        env,
    )
    if processes:
        raise RuntimeError(
            f"GPU is busy; retry when external jobs finish:\n{processes}"
        )
    for executable in ["/usr/bin/g++", "/usr/local/cuda-13.0/bin/nvcc"]:
        if not Path(executable).is_file():
            raise RuntimeError(f"Missing compiler: {executable}")
    metadata_code = (
        "import importlib.metadata as m,json,platform,sys;"
        "print(json.dumps(dict(python=platform.python_version(),"
        "architecture=platform.machine(),"
        "packages={n:m.version(n) for n in "
        "['torch','transformers','flashinfer-python']})))"
    )
    software = json.loads(capture([python, "-B", "-c", metadata_code], env))
    if software["architecture"] != "aarch64":
        raise RuntimeError("Selected interpreter must be native ARM64.")
    if tuple(map(int, software["python"].split(".")[:2])) < (3, 12):
        raise RuntimeError("The pinned PhyAI requires Python 3.12 or later.")
    versions = software["packages"]
    expected = {
        "torch": "2.11.0",
        "transformers": "5.8.1",
        "flashinfer-python": "0.6.17",
    }
    for name, version in expected.items():
        if versions[name].removeprefix("v").split("+")[0] != version:
            raise RuntimeError(f"{name}: expected {version}, got {versions[name]}")
    if "+cu" in versions["torch"] and not versions["torch"].endswith("+cu130"):
        raise RuntimeError("Use the recorded Torch CUDA 13.0 build.")
    return {"gpu": gpu, "software": software, "external_gpu_processes": processes}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "mode",
        choices=["oracle", "validate", "benchmark", "extra-oracle", "extra-validate"],
    )
    parser.add_argument("--python", default=os.environ.get("COSMOS_PYTHON"))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument(
        "--out", required=True, help="New output, relative to snapshot/"
    )
    parser.add_argument(
        "--reference", help="Official oracle directory; relative to snapshot/"
    )
    parser.add_argument("--suite", choices=["main", "shapes"], default="main")
    parser.add_argument("--pairs", type=int)
    parser.add_argument("--window-index", type=int, choices=[0, 1])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.python:
        parser.error(
            "Set --python or COSMOS_PYTHON to the Thor environment interpreter."
        )
    out = task_path(args.out)
    if not out.is_relative_to(TASK) or out in [TASK, TASK / "results"]:
        parser.error("--out must be a new run directory inside snapshot/results/.")
    if not out.is_relative_to(TASK / "results"):
        parser.error("--out must be inside snapshot/results/.")
    reference = task_path(args.reference) if args.reference else None
    candidate = args.mode in ["validate", "benchmark", "extra-validate"]
    if candidate and reference is None:
        parser.error(
            "Candidate runs require --reference from an independent official run."
        )
    if not candidate and reference:
        parser.error("Oracle creation does not take --reference.")
    if args.mode != "benchmark" and (
        args.pairs is not None or args.window_index is not None or args.suite != "main"
    ):
        parser.error("--pairs, --window-index and --suite apply to benchmark only.")
    pairs = (
        args.pairs if args.pairs is not None else (20 if args.suite == "main" else 21)
    )
    if args.mode == "benchmark" and (pairs < 20 or args.window_index is None):
        parser.error(
            "Formal E2E requires >=20 pairs and an explicit independent window."
        )
    harness = "validate_full_port_final_v4.py"
    if args.mode == "benchmark":
        harness = "paired_full_port_v5.py"
    elif args.mode.startswith("extra-"):
        harness = "validate_extra_main_paths_v5.py"
    checkpoint = args.checkpoint.expanduser().resolve()
    env = environment()
    argv = [
        args.python,
        "-B",
        str(TASK / "bench/run_with_binary_manifest_v8.py"),
        harness,
        "--checkpoint",
        str(checkpoint),
        "--out",
        str(out),
        "--backend",
        "candidate" if candidate else "official",
        "--steps",
        "4",
    ]
    if reference:
        argv += ["--reference", str(reference)]
    if args.mode == "benchmark":
        argv += ["--baseline", "official", "--pairs", str(pairs)]
        argv += ["--window-index", str(args.window_index)]
        for case in MAIN if args.suite == "main" else SHAPES:
            argv += ["--case", case]
    plan = {
        "dry_run": args.dry_run,
        "mode": args.mode,
        "argv": argv,
        "cwd": str(TASK),
        "environment": {
            k: env[k]
            for k in [
                "COSMOS_TASK_ROOT",
                "COSMOS_SOURCE_ROOT",
                "PYTHONPATH",
                "CUDA_HOME",
                "CUTE_DSL_ARCH",
                "TRITON_PTXAS_PATH",
                "TRITON_PTXAS_BLACKWELL_PATH",
                "TORCHINDUCTOR_CACHE_DIR",
                "PHYAI_KERNEL_CACHE_ROOT",
                "TRITON_CACHE_DIR",
                "CUDA_CACHE_PATH",
            ]
        },
        "source_revision": REVISION,
        "entry_sha256": hashlib.sha256(
            (TASK / "solution/candidate-full-port-v4.py").read_bytes()
        ).hexdigest(),
        "historical_gpu_result_reused": False,
    }
    if args.dry_run:
        print(json.dumps(plan, indent=2))
        return 0
    if (SOURCE / "REVISION").read_text().strip() != REVISION:
        parser.error("Unexpected pinned PhyAI revision.")
    if out.exists() and any(out.iterdir()):
        parser.error("Output directory is not empty; choose a fresh run name.")
    if not checkpoint.is_dir():
        parser.error("Checkpoint directory does not exist.")
    if reference:
        metadata = json.loads((reference / "validation.json").read_text())
        if not (
            metadata.get("backend") == "official"
            and metadata.get("complete") is True
            and metadata.get("exact_gate_passed") is True
            and (reference / "actions").is_dir()
        ):
            parser.error("Reference must be a completed independent official archive.")
    plan["preflight"] = preflight(args.python, env)
    out.mkdir(parents=True, exist_ok=True)
    (out / "launcher-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan, indent=2), flush=True)
    return subprocess.call(argv, cwd=TASK, env=env)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        raise SystemExit(f"run_thor: {error}")
