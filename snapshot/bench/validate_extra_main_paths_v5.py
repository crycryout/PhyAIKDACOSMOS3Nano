"""Extra M3542 equal-length CFG and new-stream gates with independent official archives."""
from dynamic_model_common_full_v4 import *
import contextlib

a=parser().parse_args()
engine,vae,vae_runner,counts=setup(a)
control=None
doc=dict(complete=False,exact_gate_passed=False,backend=a.backend,cases=[],errors=[],
         purpose="M3542 same CFG, equal-length different CFG, and fresh streams")
save(a.out/"validation.json",doc)
try:
    matrix=cases(a)
    _,pixels,template,_,_=next(x for x in matrix if x[0]=="len31_17")
    ids=(torch.arange(47,device="cuda",dtype=torch.long)%73+100).unsqueeze(0)
    mask=torch.ones_like(ids)
    same=dataclasses.replace(template,text_ids=ids,text_mask=mask,neg_text_ids=ids,neg_text_mask=mask)
    different=dataclasses.replace(template,text_ids=ids,text_mask=mask,neg_text_ids=ids+131,neg_text_mask=mask)
    rows=[("main_same_cfg_47",same,False),("main_same_length_different_cfg_47",different,False)]
    if a.backend=="candidate":
        assert a.reference is not None
        control=install(engine,vae)
        control.audit_proof=True;control.audit_pure=True;control.audit_signature=True
        rows+=[("main_fresh_stream_"+str(i),different,True) for i in (1,2)]
    for name,request,fresh_stream in rows:
        runner=engine.entry.scheduler.runner
        runner.reset();runner._condition_cache.clear()
        reference_name="main_same_length_different_cfg_47" if fresh_stream else name
        if control is not None:
            ref=torch.load(a.reference/"actions"/(reference_name+".pt"),map_location="cuda",weights_only=True)
        stream=torch.cuda.Stream() if fresh_stream else None
        if stream is not None:stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream) if stream is not None else contextlib.nullcontext():
            output,row=measured(lambda:run_full(control,pixels,request,vae_runner,engine),counts,request)
            if control is not None:
                equal=bool(torch.equal(output.contiguous().view(torch.uint8),ref.contiguous().view(torch.uint8)))
                row.update(byte_equal=equal,optimization=dict(control.last_request_stats),reference_sha256=action_hash(ref))
                expected=0 if name=="main_same_cfg_47" else 576
                actual=row["optimization"]["main_gemm_extension"]["counters"].get("dispatch",0)
                row.update(expected_main_dispatches=expected,actual_main_dispatches=actual)
                row["main_route_gate_passed"]=actual==expected
                if name=="main_same_cfg_47":
                    stats=row["optimization"]
                    row["inherited_same_cfg_gate"]=(stats["cfg_memo_policy"]["enabled"] and stats["physical_gen_gemms"]==576 and stats["physical_gen_attention"]==144)
                else:row["inherited_same_cfg_gate"]=True
            else:row["byte_equal"]=True
            (a.out/"actions").mkdir(exist_ok=True)
            torch.save(output.cpu(),a.out/"actions"/(name+".pt"))
        row.update(case=name,reference_case=reference_name,fresh_stream=fresh_stream,
                   positive_length=47,negative_length=47,identical_text=(name=="main_same_cfg_47"))
        doc["cases"].append(row);save(a.out/"validation.json",doc);emit("extra_main_quality",**row)
        assert row["byte_equal"],row
        if control is not None:
            assert row["main_route_gate_passed"] and row["inherited_same_cfg_gate"],row
        assert row["phase_counts"]["condition_encode"]==(1 if name=="main_same_cfg_47" else 2),row
    doc.update(complete=True,exact_gate_passed=True)
    save(a.out/"validation.json",doc)
finally:
    if control is not None:control.close()
    engine.close()
