"""Independent formal V4 route audit; flags are not execution evidence."""
from pathlib import Path
import argparse,collections,json
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
runs=[]
for family in ("main","shapes"):
    for window in (0,1):
        tag=f"formal-{family}-v4-window{window}"
        d=json.loads((t/"results"/tag/"paired-full-port-e2e.json").read_text())
        assert d["complete"] and d["gate_passed"]
        checked=[]
        for row in d["rows"]:
            if row["backend"]!="full_dynamic":continue
            o=row["optimization"];x=o["main_gemm_extension"];c=x["counters"]
            assert row["workload"]["same_cfg"] is False
            assert o["cfg_memo_policy"]["enabled"] is False
            assert o["logical_gen_gemms"]==o["physical_gen_gemms"]==1152 and o["physical_gen_attention"]==288
            assert x["additional_pack_bytes"]==1207959552 and x["additional_packed_weights"]==36
            assert x["no_cross_request_outputs"] is True
            expected=576 if family=="main" else 0
            assert c.get("dispatch",0)==expected,(tag,row["case"],c)
            if family=="main":
                assert c.get("torch_mm/cross_attention_to_out")==288 and c.get("torch_mm/mlp_down_proj")==288
            assert not c.get("configuration_fallback") and not c.get("manifest_guard_fallback")
            checked.append(dict(case=row["case"],dispatch=c.get("dispatch",0),gemm_wrapper_count=o["physical_gen_gemms"],logical_gen_gemms=o["logical_gen_gemms"],physical_gen_attention=o["physical_gen_attention"]))
        runs.append(dict(tag=tag,candidate_rows=len(checked),main_extension_dispatch_histogram=dict(collections.Counter(r["dispatch"] for r in checked)),rows=checked))
out=dict(complete=True,gate_passed=True,runs=runs,interpretation="CSE disabled-wrapper GEMM counters may be zero; actual physical 1152 launches are verified separately by same-trace correlation, while this audit requires 576 new main routes for M3542 and 0 for other M.")
(t/"results/formal-route-audit-v4.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({**out,"runs":[{k:v for k,v in r.items() if k!="rows"} for r in runs]},indent=2))
