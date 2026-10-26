"""Unprofiled full dynamic model; inherited versus request-local sampler data."""
from dynamic_model_common_full_v3 import *
from dynamic_sampler_residency_v2 import SamplerResidency
from dynamic_condition_key_ahead_v1 import RequestConditionKeys
import statistics

p=parser()
p.add_argument("--variant", action="append", default=[])
a=p.parse_args()
assert a.reference is not None
engine,vae,vae_runner,counts=setup(a)
control=None
doc=dict(complete=False,screen_only=True,baseline="full-port V3; identical controller",rows=[],results=[])
save(a.out/"sampler-residency-e2e.json",doc)
try:
    control=install(engine,vae)
    control.audit_proof=False;control.audit_pure=False;control.audit_signature=False
    residency=SamplerResidency()
    cold_keys=RequestConditionKeys(engine.entry.scheduler.runner)
    physical=collections.Counter()
    def counted(fn,label):
        def wrapped(*args,**kwargs):
            physical[label]+=1
            return fn(*args,**kwargs)
        return wrapped
    linear=control.frozen.base.linear
    linear.bindings=[(mod,old,counted(fast,"gen_gemm")) for mod,old,fast in linear.bindings]
    control.compact.bindings=[(mod,old,counted(fast,"gen_attention")) for mod,old,fast in control.compact.bindings]
    matrix=cases(a)
    assert len(matrix)==1
    name,pixels,request,use_stream,metadata=matrix[0]
    assert not use_stream and not metadata["same_cfg"]
    ref=torch.load(a.reference/"actions"/(name+".pt"),map_location="cuda",weights_only=True)
    def sample(label,index,warmup=False):
        control.set_mode("candidate")
        runner=engine.entry.scheduler.runner
        runner.reset();runner._condition_cache.clear()
        physical.clear()
        def call():
            with cold_keys.request("key_ahead" in label,request), residency.request("sigma_constants" if label.startswith("sigma_constants") else "inherited",pixels.dtype):
                return control.full(pixels,request,vae_runner,engine)
        output,row=measured(call,counts,request)
        equal=bool(torch.equal(output.contiguous().view(torch.uint8),ref.contiguous().view(torch.uint8)))
        counters=dict(residency.stats)
        expected=dict(sigma_table_uploads=2,solver_steps=2*a.steps)
        resident_ok=not label.startswith("sigma_constants") or all(counters.get(k,0)==v for k,v in expected.items())
        if label.startswith("sigma_constants"):
            resident_ok=resident_ok and counters.get("constant_uploads")==4 and counters.get("one_reuses")==14 and counters.get("half_reuses")==6 and counters.get("unintercepted_tensor",0)==0
        if "key_ahead" in label:
            resident_ok=resident_ok and cold_keys.stats.get("cold_encodes")==2 and cold_keys.stats.get("active_branch_hits")==6 and cold_keys.stats.get("host_tuple_copies")==4 and cold_keys.stats.get("host_tuple_uses")==4 and cold_keys.stats.get("unmatched_tensor_fallback",0)==0
        dispatch_ok=physical["gen_gemm"]==1152 and physical["gen_attention"]==288
        row.update(variant=label,pair=index,warmup=warmup,case=name,byte_equal=equal,
                   sampler_residency=counters,condition_key_ahead=dict(cold_keys.stats),residency_gate=resident_ok,
                   physical_counts=dict(physical),dispatch_gate=dispatch_ok,
                   optimization=dict(control.last_request_stats))
        doc["rows"].append(row)
        save(a.out/"sampler-residency-e2e.json",doc);emit("sampler_residency_sample",**row)
        assert row["phase_counts"].get("condition_encode")==2
        return row
    for variant in a.variant or ["sigma_constants","key_ahead","sigma_constants_key_ahead"]:
        result=dict(variant=variant,pairs=[],gate_passed=True);doc["results"].append(result)
        for label in ["inherited",variant]:
            for index in range(2):
                row=sample(label,index,True)
                if not all(row[k] for k in ["byte_equal","residency_gate","dispatch_gate"]):
                    result.update(gate_passed=False,rejection="byte/residency/physical-dispatch warmup gate")
        if not result["gate_passed"]:
            save(a.out/"sampler-residency-e2e.json",doc);continue
        for index in range(a.pairs):
            rows={}
            order=["inherited",variant] if index%2==0 else [variant,"inherited"]
            for label in order:
                row=sample(label,index)
                if not all(row[k] for k in ["byte_equal","residency_gate","dispatch_gate"]):
                    result.update(gate_passed=False,rejection="byte/residency/physical-dispatch gate");break
                rows[label]=row
            if not result["gate_passed"]:break
            b,c=rows["inherited"]["ready_wall_ms"],rows[variant]["ready_wall_ms"]
            result["pairs"].append(dict(pair=index,baseline_ms=b,candidate_ms=c,reduction_pct=100*(1-c/b),order=order))
            save(a.out/"sampler-residency-e2e.json",doc)
        if result["gate_passed"]:
            result["paired_median_reduction_pct"]=statistics.median(r["reduction_pct"] for r in result["pairs"])
            result["reduction_from_total_time_pct"]=100*(1-sum(r["candidate_ms"] for r in result["pairs"])/sum(r["baseline_ms"] for r in result["pairs"]))
            result["provisionally_faster"]=result["paired_median_reduction_pct"]>=1 and result["reduction_from_total_time_pct"]>=1
        emit("sampler_residency_result",**result);save(a.out/"sampler-residency-e2e.json",doc)
    doc["complete"]=True;save(a.out/"sampler-residency-e2e.json",doc)
finally:
    if control is not None:control.close()
    engine.close()
