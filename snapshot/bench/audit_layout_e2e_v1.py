"""Independent raw-row and pairing audit for experimental full-model GEMM routes."""
from pathlib import Path
import argparse,hashlib,json,statistics
p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args()
d=json.loads(a.input.read_text());assert d["complete"]
for row in d["rows"]:
    assert row["byte_equal"] and row["dispatch_proof_passed"]
    assert row["phase_counts"]==dict(vae_encode=1,engine_step=1,condition_encode=2,denoiser=8)
results=[]
for r in d["results"]:
    assert r["gate_passed"]
    pairs=r["pairs"]
    for pair in pairs:
        rows=[x for x in d["rows"] if not x["warmup"] and x["pair"]==pair["pair"]]
        selected=[x for x in rows if x["variant"]==r["variant"]]
        assert len(selected)==1 and selected[0]["ready_wall_ms"]==pair["candidate_ms"]
        bases=[x for x in rows if x["variant"]=="inherited" and x["ready_wall_ms"]==pair["baseline_ms"]]
        assert len(bases)==1
        assert abs(pair["reduction_pct"]-100*(1-pair["candidate_ms"]/pair["baseline_ms"]))<1e-9
    med=statistics.median(x["reduction_pct"] for x in pairs)
    total=100*(1-sum(x["candidate_ms"] for x in pairs)/sum(x["baseline_ms"] for x in pairs))
    assert abs(med-r["paired_median_reduction_pct"])<1e-9
    assert abs(total-r["reduction_from_total_time_pct"])<1e-9
    results.append(dict(variant=r["variant"],pairs=len(pairs),gate_passed=True,paired_median_reduction_pct=med,
                        reduction_from_total_time_pct=total,accepted_for_confirmation=med>=1 and total>=1,
                        orders=[x["order"] for x in pairs]))
audit=dict(complete=True,screen_only=True,rows=len(d["rows"]),all_bytes_phases_dispatch_passed=True,
           additional_pack_bytes=d["additional_pack_bytes"],additional_packed_weights=d["additional_packed_weights"],
           source_sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),results=results)
a.out.write_text(json.dumps(audit,indent=2)+"\n")
print(json.dumps(audit,indent=2))
