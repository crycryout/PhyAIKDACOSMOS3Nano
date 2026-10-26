#!/usr/bin/env python3
"""Independently audit archived source, raw action storage and paired timings."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import statistics
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evidence/results"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text())


def sha(data):
    return hashlib.sha256(data).hexdigest()


def close(actual, expected, location):
    require(
        math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-9),
        f"{location}: {actual!r} != {expected!r}",
    )


def storage(path):
    # Read raw storage only; never import Torch or execute pickle.
    with zipfile.ZipFile(path) as archive:
        candidates = [
            name
            for name in archive.namelist()
            if len(PurePosixPath(name).parts) >= 2
            and PurePosixPath(name).parts[-2] == "data"
            and PurePosixPath(name).name.isdigit()
        ]
        require(len(candidates) == 1, f"{path}: expected one raw tensor storage")
        orders = [name for name in archive.namelist() if name.endswith("/byteorder")]
        require(len(orders) == 1 and archive.read(orders[0]) == b"little", str(path))
        data = archive.read(candidates[0])
    require(len(data) % 2 == 0, f"{path}: odd BF16 storage length")
    words = (int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2))
    require(all((word & 0x7F80) != 0x7F80 for word in words), f"{path}: nonfinite BF16")
    return data


def metrics(pairs):
    baseline = [pair["baseline_ms"] for pair in pairs]
    candidate = [pair["candidate_ms"] for pair in pairs]
    return dict(
        pairs=len(pairs),
        official_median_ms=statistics.median(baseline),
        candidate_median_ms=statistics.median(candidate),
        paired_median_reduction_pct=statistics.median(
            100 * (1 - c / b) for b, c in zip(baseline, candidate)
        ),
        reduction_from_total_time_pct=100 * (1 - sum(candidate) / sum(baseline)),
        reduction_from_medians_pct=100
        * (1 - statistics.median(candidate) / statistics.median(baseline)),
    )


def audit():
    source = load(ROOT / "SOURCE-MANIFEST.json")
    origin = load(ROOT / "evidence/ORIGIN-MANIFEST.json")
    for manifest in [source, origin]:
        for row in manifest["files"]:
            data = (ROOT / row["path"]).read_bytes()
            require(
                len(data) == row["bytes"] and sha(data) == row["sha256"], row["path"]
            )
    require(
        sha((ROOT / source["entry"]).read_bytes()) == source["entry_sha256"],
        "Final V4 entry hash",
    )
    require(
        (ROOT / "snapshot/baseline/phyai-official/REVISION").read_text().strip()
        == source["upstream_revision"],
        "Official revision",
    )
    runtime_comparisons = 0
    for window in [0, 1]:
        runtime = load(
            RESULTS / f"formal-main-v4-window{window}/runtime-source-hashes.json"
        )
        for row in runtime["files"]:
            if row["path"].startswith(
                ("solution/", "baseline/accepted/", "baseline/phyai-official/")
            ):
                data = (ROOT / "snapshot" / row["path"]).read_bytes()
                require(
                    sha(data) == row["sha256"],
                    f"Measured runtime source: {row['path']}",
                )
                runtime_comparisons += 1

    official_doc = load(RESULTS / "official-fresh-v1/validation.json")
    require(
        official_doc["backend"] == "official" and official_doc["complete"], "Oracle"
    )
    official = {}
    for row in official_doc["cases"]:
        data = storage(RESULTS / "official-fresh-v1/actions" / (row["case"] + ".pt"))
        require(sha(data) == row["action_sha256"], f"Official action: {row['case']}")
        require(len(data) == 2 * math.prod(row["output_shape"]), row["case"])
        official[row["case"]] = data

    model_checks = []
    for folder, reference_folder in [
        ("candidate-gate-v4", "official-fresh-v1"),
        ("candidate-extra-main-v4-attempt2", "official-extra-main-v4"),
    ]:
        document = load(RESULTS / folder / "validation.json")
        require(document["complete"] and document["exact_gate_passed"], folder)
        for row in document["cases"]:
            name = row["case"]
            reference = row.get(
                "reference_case", row.get("workload", {}).get("reference_case", name)
            )
            actual = storage(RESULTS / folder / "actions" / (name + ".pt"))
            expected = storage(
                RESULTS / reference_folder / "actions" / (reference + ".pt")
            )
            require(
                actual == expected and row["byte_equal"] is True, f"Raw action: {name}"
            )
            require(
                len(actual) == 2 * math.prod(row["output_shape"]),
                f"Action shape: {name}",
            )
            require(
                sha(actual) == row["action_sha256"] == row["reference_sha256"], name
            )
            model_checks.append(
                {"case": name, "bytes": len(actual), "sha256": sha(actual)}
            )
    require(len(model_checks) == 29, "Expected 25 + 4 model action comparisons")

    main_pairs, all_pairs, windows = [], [], []
    timed_rows = 0
    process_ids = []
    for family, expected_count in [("main", 20), ("shapes", 21)]:
        for window in [0, 1]:
            folder = RESULTS / f"formal-{family}-v4-window{window}"
            doc = load(folder / "paired-full-port-e2e.json")
            require(doc["complete"] and doc["gate_passed"], str(folder))
            require(doc["baseline"] == "official", "Baseline must be original official")
            require(doc["independent_process_window"] == window, "Independent window")
            require(len(doc["pairs"]) == expected_count, "Formal pair count")
            process_ids.append(load(folder / "environment.json")["pid"])
            formal = {}
            for row in doc["rows"]:
                require(row["byte_equal"] is True, "Timed output byte gate")
                require(row["output_dtype"] == "torch.bfloat16", "Timed BF16 output")
                require(
                    row["phase_counts"]
                    == {
                        "vae_encode": 1,
                        "engine_step": 1,
                        "condition_encode": 2,
                        "denoiser": 8,
                    },
                    "Matched E2E phase counts",
                )
                require(sha(official[row["case"]]) == row["action_sha256"], row["case"])
                require(
                    row["ready_wall_ms"] > 0 and row["event_ms"] > 0, "Positive timing"
                )
                if not row["calibration"]:
                    key = (row["pair"], row["case"], row["backend"])
                    require(key not in formal, f"Duplicate timing row {key}")
                    formal[key] = row
            require(len(formal) == 2 * expected_count, "No dropped formal rows")
            for pair in doc["pairs"]:
                baseline = formal[(pair["pair"], pair["case"], "official")]
                candidate = formal[(pair["pair"], pair["case"], "full_dynamic")]
                close(pair["baseline_ms"], baseline["ready_wall_ms"], "Baseline timing")
                close(
                    pair["candidate_ms"], candidate["ready_wall_ms"], "Candidate timing"
                )
                close(
                    pair["reduction_pct"],
                    100 * (1 - pair["candidate_ms"] / pair["baseline_ms"]),
                    "Paired reduction",
                )
                expected_order = (
                    ["official", "full_dynamic"]
                    if (window + pair["pair"]) % 2 == 0
                    else ["full_dynamic", "official"]
                )
                require(pair["order"] == expected_order, "AB/BA order")
                require(
                    pair["candidate_action_sha256"]
                    == pair["baseline_action_sha256"]
                    == candidate["action_sha256"]
                    == baseline["action_sha256"],
                    "Paired action hashes",
                )
            require(len(doc["calibration"]) == 1, "One A/A calibration per window")
            for calibration in doc["calibration"]:
                signed = [
                    100 * (row["second_ms"] / row["first_ms"] - 1)
                    for row in calibration["pairs"]
                ]
                median = statistics.median(signed)
                close(median, calibration["median_signed_difference_pct"], "A/A median")
                require(calibration["passed"] is True and abs(median) <= 3, "A/A gate")
            observed = metrics(doc["pairs"])
            close(
                observed["paired_median_reduction_pct"],
                doc["all_pairs"]["paired_median_reduction_pct"],
                "Window summary",
            )
            windows.append(dict(family=family, window=window, **observed))
            timed_rows += len(doc["rows"])
            all_pairs += doc["pairs"]
            if family == "main":
                main_pairs += doc["pairs"]
    require(len(set(process_ids)) == 4, "Four independent formal model processes")
    require(len(all_pairs) == 82 and timed_rows == 196, "Full formal evidence count")
    summary = load(RESULTS / "main-summary-v4.json")
    observed = metrics(main_pairs)
    for key, value in observed.items():
        close(value, summary["pooled"][key], f"Main pooled {key}")
    for name, recorded in summary["by_case"].items():
        for key, value in metrics(
            [pair for pair in main_pairs if pair["case"] == name]
        ).items():
            close(value, recorded[key], f"{name} {key}")

    trace = ROOT / "evidence/workflow/dynamic-full-port.jsonl"
    provenance = load(ROOT / "evidence/workflow/trace-provenance.json")
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    require(
        sha(trace.read_bytes()) == provenance["export_sha256"], "Workflow export hash"
    )
    require(len(events) == provenance["events"], "Workflow event count")
    require(
        dict(Counter(row["event"] for row in events)) == provenance["counts"],
        "Trace counts",
    )
    require(
        [row for row in events if row["event"] == "workflow.read"]
        == load(ROOT / "evidence/workflow/read-events.json"),
        "All read events retained",
    )

    syntax_count = 0
    for path in [*ROOT.glob("scripts/*.py"), *(ROOT / "snapshot").rglob("*.py")]:
        compile(path.read_bytes(), str(path.relative_to(ROOT)), "exec")
        syntax_count += 1
    delivery = ROOT / "DELIVERY-MANIFEST.json"
    if delivery.exists():
        for row in load(delivery)["files"]:
            data = (ROOT / row["path"]).read_bytes()
            require(
                sha(data) == row["sha256"] and len(data) == row["bytes"], row["path"]
            )
    return dict(
        passed=True,
        method="Python standard library only; no GPU, Torch imports, or pickle execution",
        new_gpu_measurements=False,
        source_files=len(source["files"]),
        historical_runtime_source_comparisons=runtime_comparisons,
        origin_files=len(origin["files"]),
        model_storage_comparisons=len(model_checks),
        formal_pairs=len(all_pairs),
        timed_outputs=timed_rows,
        main=observed,
        windows=windows,
        workflow_events=len(events),
        read_events=provenance["counts"]["workflow.read"],
        python_syntax_files=syntax_count,
        model_storage_checks=model_checks,
        limits="Archived finite BF16 actions and tested shapes only; no layerwise universal proof or LIBERO rollout.",
    )


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "model_storage_checks"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
