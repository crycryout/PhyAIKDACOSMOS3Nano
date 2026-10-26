"""Independent stdlib-only audit of saved BF16 tensor storages and paired timings."""
from pathlib import Path
import argparse,hashlib,json,math,statistics,zipfile
p=argparse.ArgumentParser()
p.add_argument("--task",type=Path,required=True)
a=p.parse_args(); t=a.task
def load(rel):return json.loads((t/rel).read_text())
def storage(path):
    with zipfile.ZipFile(path) as z:
        names=[n for n in z.namelist() if "/data/" in n]
        assert len(names)==1,(path,names)
        raw=z.read(names[0])
    return raw,hashlib.sha256(raw).hexdigest()
official=load("results/official-v2/validation.json")
assert official["complete"] and official["exact_gate_passed"] and not official["errors"]
refs={r["case"]:r for r in official["cases"]}
assert len(refs)==20
rows=[]
for variant in ("official-v2","candidate-v2","candidate-v3"):
    doc=load("results/"+variant+"/validation.json")
    assert doc["complete"] and doc["exact_gate_passed"] and not doc["errors"]
    assert set(r["case"] for r in doc["cases"])==set(refs)
    for r in doc["cases"]:
        name=r["case"]; raw,h=storage(t/"results"/variant/"actions"/(name+".pt"))
        expected,h_expected=storage(t/"results/official-v2/actions"/(name+".pt"))
        assert raw==expected and h==h_expected==r["action_sha256"]==refs[name]["action_sha256"],(variant,name)
        assert len(raw)==2*math.prod(r["output_shape"]),(variant,name)
        rows.append(dict(variant=variant,case=name,raw_bf16_bytes=len(raw),sha256=h,byte_equal=True))
paired=load("results/paired-e2e-v3/paired-dynamic-e2e.json")
assert paired["complete"] and paired["gate_passed"] and len(paired["rows"])==24
for r in paired["rows"]:
    assert r["byte_equal"] and r["action_sha256"]==refs[r["case"]]["action_sha256"]
    assert r["phase_counts"]==dict(vae_encode=1,engine_step=1,condition_encode=2,denoiser=8),r
    assert r["workload"]["same_cfg"] is False
    assert r["output_dtype"]=="torch.bfloat16" and r["ready_wall_ms"]>0
summary={}
for w in (0,1):
    grouped=[r for r in paired["rows"] if r["window"]==w]
    assert len(grouped)==12
    av=[r["ready_wall_ms"] for r in grouped if r["backend"]=="official"]
    bv=[r["ready_wall_ms"] for r in grouped if r["backend"]=="candidate"]
    am,bm=statistics.median(av),statistics.median(bv)
    reduction=(1-bm/am)*100
    reported=paired["summary"][str(w)]
    assert math.isclose(am,reported["official_median_ms"],abs_tol=1e-9)
    assert math.isclose(bm,reported["candidate_median_ms"],abs_tol=1e-9)
    assert math.isclose(reduction,reported["reduction_from_medians_pct"],abs_tol=1e-9) and reduction>=30
    for i in range(6):
        rr=[r for r in grouped if r["pair"]==i]
        assert len(rr)==2 and len({r["case"] for r in rr})==1
        assert [r["backend"] for r in rr]==(["official","candidate"] if i%2==0 else ["candidate","official"])
    summary[str(w)]=dict(official_median_ms=am,candidate_median_ms=bm,reduction_pct=reduction,pairs=6)
report=dict(complete=True,gate_passed=True,method="zipfile reads one raw BF16 storage; does not import torch or unpickle",
            storage_comparisons=len(rows),official_cases=20,candidate_v2_cases=20,candidate_v3_cases=20,
            timed_rows_checked=24,all_timed_cases_have_different_cfg_text=True,
            denominator="original official only; no additional 30% claim against R3 best",summary=summary,rows=rows)
(t/"results/independent-evidence-audit-v2.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="rows"},indent=2))
