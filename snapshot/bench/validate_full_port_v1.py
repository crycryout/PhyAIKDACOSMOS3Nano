"""Independent official archives followed by dynamic full-model byte gates."""
from dynamic_model_common_full_v1 import *
import contextlib

a=parser().parse_args()
engine,vae,vae_runner,counts=setup(a)
control=None
doc=dict(complete=False,exact_gate_passed=False,backend=a.backend,cases=[],errors=[])
save(a.out/"validation.json",doc)
try:
    matrix=cases(a)
    if a.backend=="candidate":
        assert a.reference is not None
        control=install(engine,vae)
        from validate_dynamic_attention_v2 import validate
        validate(control,a.out,save)
        control.audit_proof=True
        control.audit_pure=True
        control.audit_signature=True
    stream=torch.cuda.Stream();stream.wait_stream(torch.cuda.current_stream())
    for name,pixels,request,use_stream,metadata in matrix:
        with torch.cuda.stream(stream) if use_stream else contextlib.nullcontext():
            output,row=measured(lambda:run_full(control,pixels,request,vae_runner,engine),counts,request)
            if control is not None:
                row["optimization"]=dict(control.last_request_stats)
                ref=torch.load(a.reference/"actions"/(name+".pt"),map_location="cuda",weights_only=True)
                equal=bool(torch.equal(ref.contiguous().view(torch.uint8),output.contiguous().view(torch.uint8)))
                delta=output.float()-ref.float()
                row.update(byte_equal=equal,reference_sha256=action_hash(ref),
                    max_abs=float(delta.abs().max()),relative_l2=float(delta.norm()/ref.float().norm().clamp_min(1e-12)))
            else:row["byte_equal"]=True
            (a.out/"actions").mkdir(exist_ok=True)
            torch.save(output.cpu(),a.out/"actions"/(name+".pt"))
        row.update(case=name,workload=metadata)
        doc["cases"].append(row);save(a.out/"validation.json",doc)
        emit("quality",**row)
        assert row["byte_equal"],("BF16 byte gate failed",name,row)
        if control is not None:
            assert len(control.compact.plans)<=control.compact.max_plans
            if row["optimization"]["dynamic"]["route"]=="optimized_eager":
                assert row["optimization"]["dynamic"]["pair_state_cleared"],row
    doc["complete"]=True;doc["exact_gate_passed"]=True
    save(a.out/"validation.json",doc)
finally:
    if control is not None:control.close()
    engine.close()
