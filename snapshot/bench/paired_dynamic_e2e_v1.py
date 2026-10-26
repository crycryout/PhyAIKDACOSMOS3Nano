"""Paired unprofiled dynamic E2E with independent original action references."""
from dynamic_model_common_v1 import *
import statistics

a=parser().parse_args()
assert a.reference is not None and not a.cuda_graph
engine,vae,vae_runner,counts=setup(a)
control=None
doc=dict(complete=False,gate_passed=False,reference="independent original official archives",
    timing_boundary="GPU pixels -> online VAE -> original engine.step -> ready GPU BF16 actions",
    condition_regime="cold UND conditions per measured request; all 2 branches encoded",
    warmup="two untimed full requests per mode; compilation excluded equally",
    backend_order="adjacent pairs, reversed every pair; 2 windows",
    rows=[],pairs=[],summary={})
save(a.out/"paired-dynamic-e2e.json",doc)
try:
    matrix=cases(a)
    control=install(engine,vae)
    control.audit_proof=False;control.audit_pure=False;control.audit_signature=False
    refs={name:torch.load(a.reference/"actions"/(name+".pt"),map_location="cuda",weights_only=True)
          for name,_,_,_,_ in matrix}
    name,pixels,request,_,_=matrix[0]
    for mode in ("official","candidate"):
        control.set_mode(mode)
        for index in range(2):
            _,row=measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
            emit("warmup",backend=mode,index=index,**row)
    for window in range(2):
        pairs=[]
        for index in range(a.pairs):
            name,pixels,request,use_stream,metadata=matrix[index%len(matrix)]
            assert not use_stream
            outputs={};rows={}
            order=("official","candidate") if (window+index)%2==0 else ("candidate","official")
            for mode in order:
                control.set_mode(mode)
                engine.entry.scheduler.runner.invalidate_cache()
                output,row=measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
                equal=bool(torch.equal(output.contiguous().view(torch.uint8),refs[name].contiguous().view(torch.uint8)))
                row.update(window=window,pair=index,case=name,backend=mode,byte_equal=equal,
                           workload=metadata,optimization=dict(control.last_request_stats) if mode=="candidate" else None)
                doc["rows"].append(row);save(a.out/"paired-dynamic-e2e.json",doc)
                emit("measure",**row)
                assert equal,("Independent byte gate during timing",row)
                assert row["phase_counts"].get("condition_encode")==2,row
                rows[mode]=row
            b,c=rows["official"]["ready_wall_ms"],rows["candidate"]["ready_wall_ms"]
            pair=dict(window=window,pair=index,case=name,official_ms=b,candidate_ms=c,
                      reduction_pct=(1-c/b)*100,order=list(order))
            pairs.append(pair);doc["pairs"].append(pair);emit("pair",**pair)
            save(a.out/"paired-dynamic-e2e.json",doc)
        bs=[p["official_ms"] for p in pairs];cs=[p["candidate_ms"] for p in pairs]
        doc["summary"][str(window)]=dict(samples=len(pairs),official_median_ms=statistics.median(bs),
            candidate_median_ms=statistics.median(cs),
            reduction_from_medians_pct=(1-statistics.median(cs)/statistics.median(bs))*100,
            paired_median_reduction_pct=statistics.median(p["reduction_pct"] for p in pairs),
            all_bytes_equal=True)
        save(a.out/"paired-dynamic-e2e.json",doc)
    doc["complete"]=True;doc["gate_passed"]=True
    doc["at_least_30pct_vs_original_official"]=all(v["reduction_from_medians_pct"]>=30 for v in doc["summary"].values())
    doc["another_30pct_vs_R3_best"]="not_established_by_this_original-official comparison"
    save(a.out/"paired-dynamic-e2e.json",doc)
finally:
    if control is not None:control.close()
    engine.close()
