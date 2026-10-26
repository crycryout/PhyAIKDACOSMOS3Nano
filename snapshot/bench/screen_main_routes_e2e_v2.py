"""Complete-model E2E screening of M3542 choices in the distinct-CFG workload."""
from dynamic_model_common_full_v3 import *
from main_gemm_routes_v2 import MainGemmRoutes
import statistics
p=parser();p.add_argument("--selection",type=Path);p.add_argument("--variant",action="append",default=[])
a=p.parse_args();assert a.reference is not None
engine,vae,vae_runner,counts=setup(a);control=None;routes=None
doc=dict(complete=False,screen_only=True,baseline="inherited physical dynamic V3 under same controller",rows=[],results=[])
save(a.out/"main-route-e2e.json",doc)
try:
    control=install(engine,vae);control.audit_proof=False;control.audit_pure=False;control.audit_signature=False
    selected=json.loads(a.selection.read_text())["configurations"].get("3542",{}) if a.selection else {}
    routes=MainGemmRoutes(control.frozen.base.linear,selected)
    matrix=cases(a);assert len(matrix)==1
    name,pixels,request,use_stream,metadata=matrix[0]
    assert not use_stream and not metadata["same_cfg"]
    ref=torch.load(a.reference/"actions"/(name+".pt"),map_location="cuda",weights_only=True)
    variants=a.variant or ["torch_all"]+["torch:"+c for c in routes.categories]
    if selected and not a.variant:variants+=["selected_all"]+["selected:"+c for c in selected]
    def sample(label,index,warmup=False):
        routes.set_variant(label);control.set_mode("candidate")
        runner=engine.entry.scheduler.runner;runner.reset();runner._condition_cache.clear()
        before=routes.stats.copy()
        output,row=measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
        equal=bool(torch.equal(output.contiguous().view(torch.uint8),ref.contiguous().view(torch.uint8)))
        row.update(variant=label,pair=index,warmup=warmup,case=name,byte_equal=equal,
                   main_route_counters=dict(routes.stats-before),expected_main_dispatches=288*len(routes.active),dispatch_proof_passed=(routes.stats-before).get("dispatch",0)==288*len(routes.active),optimization=dict(control.last_request_stats))
        doc["rows"].append(row);save(a.out/"main-route-e2e.json",doc)
        emit("main_route_sample",**row)
        assert row["phase_counts"].get("condition_encode")==2
        return row
    for variant in variants:
        result=dict(variant=variant,pairs=[],gate_passed=True);doc["results"].append(result)
        routes.set_variant(variant)
        if not routes.active:
            result.update(gate_passed=False,rejection="No selected configurations for this variant")
            continue
        for label in ["inherited",variant]:
            for index in range(2):
                row=sample(label,index,True)
                if not row["byte_equal"] or not row["dispatch_proof_passed"]:result.update(gate_passed=False,rejection="BF16 byte or actual-dispatch gate failed during warmup")
        if not result["gate_passed"]:
            save(a.out/"main-route-e2e.json",doc);continue
        for index in range(a.pairs):
            rows={}
            order=["inherited",variant] if index%2==0 else [variant,"inherited"]
            for label in order:
                row=sample(label,index)
                if not row["byte_equal"] or not row["dispatch_proof_passed"]:
                    result.update(gate_passed=False,rejection="BF16 byte or actual-dispatch gate failed");break
                rows[label]=row
            if not result["gate_passed"]:break
            b,c=rows["inherited"]["ready_wall_ms"],rows[variant]["ready_wall_ms"]
            result["pairs"].append(dict(pair=index,baseline_ms=b,candidate_ms=c,reduction_pct=100*(1-c/b),order=order))
            save(a.out/"main-route-e2e.json",doc)
        if result["gate_passed"]:
            result["paired_median_reduction_pct"]=statistics.median(r["reduction_pct"] for r in result["pairs"])
            result["reduction_from_total_time_pct"]=100*(1-sum(r["candidate_ms"] for r in result["pairs"])/sum(r["baseline_ms"] for r in result["pairs"]))
            result["provisionally_faster"]=result["paired_median_reduction_pct"]>=1 and result["reduction_from_total_time_pct"]>=1
        emit("main_route_result",**result);save(a.out/"main-route-e2e.json",doc)
    doc["complete"]=True;save(a.out/"main-route-e2e.json",doc)
finally:
    if routes is not None:routes.close()
    if control is not None:control.close()
    engine.close()
