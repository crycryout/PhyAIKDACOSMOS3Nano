"""Independent storage/phase/order/statistics audit; stdlib only, no torch or pickle."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import statistics
import zipfile
p=argparse.ArgumentParser()
p.add_argument("--task",type=Path,required=True)
p.add_argument("--candidate",default="candidate-gate-v1")
p.add_argument("--paired",action="append",default=[])
p.add_argument("--output",type=Path,required=True)
a=p.parse_args();task=a.task
def read(rel):return json.loads((task/rel).read_text())
def storage(path):
    with zipfile.ZipFile(path) as archive:
        names=[name for name in archive.namelist() if "/data/" in name]
        assert len(names)==1,(str(path),names)
        raw=archive.read(names[0])
    return raw,hashlib.sha256(raw).hexdigest()
official=read("results/official-fresh-v1/validation.json")
assert official["complete"] and official["exact_gate_passed"] and len(official["cases"])==22
refs={r["case"]:r for r in official["cases"]}
report=dict(complete=False,gate_passed=False,method="zipfile reads only the single raw BF16 storage; never imports torch or unpickles",
            inherited_oracle_comparisons=[],official_storage_checks=[],candidate_storage_checks=[],paired_audits={})
for name,row in refs.items():
    raw,h=storage(task/"results/official-fresh-v1/actions"/(name+".pt"))
    assert h==row["action_sha256"] and len(raw)==2*math.prod(row["output_shape"])
    report["official_storage_checks"].append(dict(case=name,sha256=h,bytes=len(raw)))
    old=task/"baseline/dynamic-official-oracle/actions"/(name+".pt")
    if old.exists():
        old_raw,old_h=storage(old)
        assert raw==old_raw and h==old_h,("original official output changed",name)
        report["inherited_oracle_comparisons"].append(dict(case=name,sha256=h,byte_equal=True))
assert len(report["inherited_oracle_comparisons"])==20
candidate_path=task/"results"/a.candidate/"validation.json"
if candidate_path.exists():
    candidate=json.loads(candidate_path.read_text())
    assert candidate["complete"] and candidate["exact_gate_passed"] and len(candidate["cases"])==25
    for row in candidate["cases"]:
        name=row["case"];refname=row["workload"].get("reference_case",name)
        raw,h=storage(task/"results"/a.candidate/"actions"/(name+".pt"))
        expected,he=storage(task/"results/official-fresh-v1/actions"/(refname+".pt"))
        assert raw==expected and h==he==row["action_sha256"]==refs[refname]["action_sha256"],(name,refname)
        assert row["byte_equal"] and len(raw)==2*math.prod(row["output_shape"])
        report["candidate_storage_checks"].append(dict(case=name,reference_case=refname,bytes=len(raw),sha256=h))
def recompute(pairs):
    bs=[r["baseline_ms"] for r in pairs];cs=[r["candidate_ms"] for r in pairs]
    return dict(samples=len(pairs),baseline_median_ms=statistics.median(bs),candidate_median_ms=statistics.median(cs),
        reduction_from_medians_pct=100*(1-statistics.median(cs)/statistics.median(bs)),
        paired_median_reduction_pct=statistics.median(100*(1-c/b) for b,c in zip(bs,cs)),
        reduction_from_total_time_pct=100*(1-sum(cs)/sum(bs)))
for rel in a.paired:
    d=read(rel)
    assert d["complete"] and d["gate_passed"]
    baseline=d["baseline"];raw_rows=d["rows"]
    for row in raw_rows:
        assert row["byte_equal"] and row["action_sha256"]==refs[row["case"]]["action_sha256"]
        assert row["phase_counts"]==dict(vae_encode=1,engine_step=1,condition_encode=2,denoiser=8),row
        assert row["workload"]["same_cfg"] is False
        assert row["ready_wall_ms"]>0 and row["output_dtype"]=="torch.bfloat16"
        if row["backend"]=="full_dynamic":
            assert row["optimization"]["cfg_memo_policy"]["enabled"] is False
            assert row["optimization"]["physical_gen_attention"]==288
            assert row["optimization"]["logical_gen_gemms"]==1152
    results={}
    for window in [0,1]:
        pairs=[r for r in d["pairs"] if r["window"]==window]
        assert len(pairs)==d["formal_pair_count_per_window"]
        if baseline=="official":assert len(pairs)>=20
        for pair in pairs:
            index=pair["pair"]
            rows=[r for r in raw_rows if r["window"]==window and r["pair"]==index and not r["calibration"]]
            order=[baseline,"full_dynamic"] if (window+index)%2==0 else ["full_dynamic",baseline]
            assert [r["backend"] for r in rows]==order==pair["order"]
            assert len({r["case"] for r in rows})==1 and rows[0]["case"]==pair["case"]
            by_backend={r["backend"]:r for r in rows}
            assert by_backend[baseline]["ready_wall_ms"]==pair["baseline_ms"]
            assert by_backend["full_dynamic"]["ready_wall_ms"]==pair["candidate_ms"]
        result=recompute(pairs)
        for key,value in result.items():assert math.isclose(value,d["summary"][str(window)][key],rel_tol=1e-12,abs_tol=1e-8),(rel,window,key)
        result["by_case"]={name:recompute([r for r in pairs if r["case"]==name]) for name in sorted({r["case"] for r in pairs})}
        results[str(window)]=result
    for calibration in d.get("calibration",[]):
        med=statistics.median(r["signed_difference_pct"] for r in calibration["pairs"])
        assert math.isclose(med,calibration["median_signed_difference_pct"],abs_tol=1e-10)
        assert abs(med)<=calibration["acceptance_abs_median_pct"] and calibration["passed"]
    report["paired_audits"][rel]=dict(baseline=baseline,rows_checked=len(raw_rows),pairs_checked=len(d["pairs"]),windows=results,pooled=recompute(d["pairs"]))
report.update(complete=True,gate_passed=True)
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({key:value for key,value in report.items() if key not in ["official_storage_checks","candidate_storage_checks","inherited_oracle_comparisons"]},indent=2))
print(json.dumps({"official_storage_checks":len(report["official_storage_checks"]),"candidate_storage_checks":len(report["candidate_storage_checks"]),"inherited_oracle_equal":len(report["inherited_oracle_comparisons"])}))
