"""Audit final runtime identity, fixed source/config bytes, binary hashes, and process independence."""
from pathlib import Path
import argparse,collections,hashlib,json
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
read=lambda rel:json.loads((t/rel).read_text())
frozen=read("contracts/full-port-v3-frozen-hashes.json")
for rel,expected in frozen.items():assert hashlib.sha256((t/rel).read_bytes()).hexdigest()==expected,rel
required={k:v for k,v in frozen.items() if not k.startswith("contracts/") and not k.endswith("run_formal_queue_v2.py")}
tags=[f"formal-{family}-v3-window{w}" for family in ("main","shapes") for w in (0,1)]
report=dict(complete=False,gate_passed=False,runs=[],shared_mapped_binary_hashes={})
pidset=set();shared=collections.defaultdict(set)
for tag in tags:
    folder=t/"results"/tag
    run=read(f"results/{tag}/run.json");env=read(f"results/{tag}/environment.json")
    src=read(f"results/{tag}/runtime-source-hashes.json");binary=read(f"results/{tag}/runtime-binary-hashes.json")
    data=read(f"results/{tag}/paired-full-port-e2e.json")
    assert run["returncode"]==0 and run["interference_observed"] is False and run["profile"]=="none"
    assert run["before"]["hostname"]=="haruhikage" and run["before"]["architecture"]=="aarch64"
    assert run["workflow_trace_id"]=="wf-20261023T191907391908Z-63abb6795e"
    assert env["source_revision"]=="75403624f9c8858f347f624e3b032553fa756ac2"
    assert env["dtype"]=="BF16" and env["runtime_cuda_graph"] is False and env["capability"]==[11,0]
    assert env["pid"]==src["pid"]==binary["pid"] and env["pid"] not in pidset
    pidset.add(env["pid"])
    index={r["path"]:r["sha256"] for r in src["files"]}
    for rel,h in required.items():assert index.get(rel)==h,(tag,rel,index.get(rel),h)
    assert data["complete"] and data["gate_passed"] and data["baseline"]=="official"
    assert data["window_indices"]==[int(tag[-1])] and data["independent_process_window"]==int(tag[-1])
    assert len(data["calibration"])==1 and data["calibration"][0]["passed"]
    expected=20 if "main" in tag else 21
    assert len(data["pairs"])==expected and len(data["rows"])==2*expected+8
    for r in binary["mapped_binaries"]:
        assert r.get("sha256") and not r.get("error"),r
        shared[r["path"]].add(r["sha256"])
    samples=run["telemetry"]
    clocks=collections.Counter()
    for sample in samples:
        key=json.dumps(sample.get("clocks_hz"),sort_keys=True)
        clocks[key]+=1
    report["runs"].append(dict(tag=tag,pid=env["pid"],pairs=len(data["pairs"]),rows=len(data["rows"]),source_files=len(src["files"]),required_runtime_files_verified=len(required),mapped_binaries=len(binary["mapped_binaries"]),telemetry_samples=len(samples),observed_clock_samples=dict(clocks),aa_median_signed_difference_pct=data["calibration"][0]["median_signed_difference_pct"],returncode=0,interference_observed=False,workflow_event_id=run["workflow_event_id"]))
for path,values in shared.items():assert len(values)==1,("Mapped library changed",path,values)
report["shared_mapped_binary_hashes"]={k:next(iter(v)) for k,v in shared.items()}
report.update(complete=True,gate_passed=True,independent_model_pids=sorted(pidset),formal_pairs_total=sum(r["pairs"] for r in report["runs"]),timed_rows_total=sum(r["rows"] for r in report["runs"]))
(t/"results/release-runtime-audit-v3.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="shared_mapped_binary_hashes"},indent=2))
