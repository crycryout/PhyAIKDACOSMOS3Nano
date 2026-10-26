"""Isolate dynamic Lt categories under complete request memory/cache context."""
from dynamic_model_common_full_v1 import *
import copy
import statistics
a=parser().parse_args()
assert a.reference is not None
engine,vae,vae_runner,counts=setup(a)
control=None
doc=dict(complete=False,screen_only=True,rows=[],results=[])
save(a.out/"category-e2e.json",doc)
try:
    control=install(engine,vae)
    all_configs=copy.deepcopy(control.dynamic_lt.selected)
    final=copy.deepcopy(all_configs)
    matrix=cases(a)
    for case in matrix:
        name,pixels,request,use_stream,metadata=case
        assert not use_stream and name in ("video17frames","action16")
        m="1982" if name=="video17frames" else "3526"
        ref=torch.load(a.reference/"actions"/(name+".pt"),map_location="cuda",weights_only=True)
        for enabled in [False,True]:
            control.dynamic_lt.selected=all_configs
            control.dynamic_lt.set_enabled(enabled);control.set_mode("candidate")
            for _ in range(2):
                runner=engine.entry.scheduler.runner;runner.reset();runner._condition_cache.clear()
                measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
        accepted={}
        for category,spec in all_configs[m].items():
            result=dict(case=name,M=int(m),category=category,pairs=[])
            doc["results"].append(result)
            control.dynamic_lt.selected={m:{category:spec}}
            for index in range(a.pairs):
                rows={}
                order=["parent_dynamic","category_only"] if index%2==0 else ["category_only","parent_dynamic"]
                for label in order:
                    control.dynamic_lt.set_enabled(label=="category_only");control.set_mode("candidate")
                    runner=engine.entry.scheduler.runner;runner.reset();runner._condition_cache.clear()
                    output,row=measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
                    exact=bool(torch.equal(output.contiguous().view(torch.uint8),ref.contiguous().view(torch.uint8)))
                    row.update(case=name,M=int(m),category=category,pair=index,variant=label,byte_equal=exact,optimization=dict(control.last_request_stats))
                    doc["rows"].append(row);save(a.out/"category-e2e.json",doc)
                    assert exact and row["phase_counts"].get("condition_encode")==2,row
                    rows[label]=row
                b,c=rows["parent_dynamic"]["ready_wall_ms"],rows["category_only"]["ready_wall_ms"]
                result["pairs"].append(dict(pair=index,baseline_ms=b,candidate_ms=c,reduction_pct=100*(1-c/b),order=order))
                save(a.out/"category-e2e.json",doc)
            result["paired_median_reduction_pct"]=statistics.median(r["reduction_pct"] for r in result["pairs"])
            result["reduction_from_total_time_pct"]=100*(1-sum(r["candidate_ms"] for r in result["pairs"])/sum(r["baseline_ms"] for r in result["pairs"]))
            result["accepted"]=result["paired_median_reduction_pct"]>=1.0 and result["reduction_from_total_time_pct"]>=1.0
            if result["accepted"]:accepted[category]=spec
            emit("dynamic_lt_category_e2e",**result)
            save(a.out/"category-e2e.json",doc)
        if accepted:final[m]=accepted
        else:final.pop(m,None)
    selected=dict(status="category_e2e_screen_selected_requires_final_bundle_and_byte_gate",configurations=final,
                  selection="retain M1472 bundle; M1982/M3526 categories require >=1% median and aggregate complete-E2E reduction")
    save(a.out/"dynamic-lt-selected-v2.json",selected)
    doc["complete"]=True;save(a.out/"category-e2e.json",doc)
finally:
    if control is not None:control.close()
    engine.close()
