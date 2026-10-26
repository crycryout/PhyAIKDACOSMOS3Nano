"""Recompute experimental E2E without importing Torch or promoting failed gates."""
from pathlib import Path
import argparse,hashlib,json,statistics
p=argparse.ArgumentParser()
p.add_argument("--input",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args()
d=json.loads(a.input.read_text())
assert d["complete"]
results=[]
for result in d["results"]:
    pairs=result["pairs"]
    row=dict(variant=result["variant"],gate_passed=result["gate_passed"],pairs=len(pairs))
    if pairs:
        med=statistics.median(100*(1-r["candidate_ms"]/r["baseline_ms"]) for r in pairs)
        total=100*(1-sum(r["candidate_ms"] for r in pairs)/sum(r["baseline_ms"] for r in pairs))
        assert abs(med-result["paired_median_reduction_pct"])<1e-9
        assert abs(total-result["reduction_from_total_time_pct"])<1e-9
        row.update(paired_median_reduction_pct=med,reduction_from_total_time_pct=total,
                   accepted_for_confirmation=result["gate_passed"] and med>=1 and total>=1)
    else:
        row.update(rejection=result.get("rejection"),accepted_for_confirmation=False)
    relevant=[r for r in d["rows"] if r["variant"]==result["variant"]]
    row["actual_failed_rows"]=[{k:r.get(k) for k in ["pair","warmup","byte_equal","residency_gate","dispatch_gate","sampler_residency","condition_key_ahead"]} for r in relevant if not all(r.get(k) for k in ["byte_equal","residency_gate","dispatch_gate"])]
    assert result["gate_passed"] == (not row["actual_failed_rows"])
    if result["gate_passed"]:assert pairs
    results.append(row)
audit=dict(complete=True,screen_only=True,source_sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),
           rows=len(d["rows"]),all_outputs_byte_equal=all(r["byte_equal"] for r in d["rows"]),
           all_physical_counts_passed=all(r["dispatch_gate"] for r in d["rows"]),results=results)
a.out.parent.mkdir(parents=True,exist_ok=True)
a.out.write_text(json.dumps(audit,indent=2)+"\n")
print(json.dumps(audit,indent=2))
