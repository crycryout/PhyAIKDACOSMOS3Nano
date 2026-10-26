"""Candidate-only native Torch trace of an actual text-length transition."""
from dynamic_model_common_full_v3 import *
from torch.profiler import profile,ProfilerActivity,record_function

a=parser().parse_args()
assert a.reference is not None
engine,vae,vae_runner,counts=setup(a)
control=None
try:
    matrix={row[0]:row for row in cases(a)}
    control=install(engine,vae)
    _,pixels,request,_,_=matrix["len31_17"]
    for i in range(2):
        measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
    def scope(fn,label):
        def wrapped(*args,**kwargs):
            with record_function(label):return fn(*args,**kwargs)
        return wrapped
    names={id(mod):name for name,mod in engine.entry.transformer.named_modules()}
    linear=control.frozen.base.linear
    linear.bindings=[(mod,old,scope(fast,"cosmos3_GEN_GEMM/"+names[id(mod)]))
                     for mod,old,fast in linear.bindings]
    control.compact.bindings=[(mod,old,scope(fast,"cosmos3_GEN_ATTENTION/L"+str(index)))
                             for index,(mod,old,fast) in enumerate(control.compact.bindings)]
    control.original_transformer=scope(control.original_transformer,"cosmos3_stage/GEN_forward")
    vae_runner.encode=scope(vae_runner.encode,"cosmos3_stage/VAE_encode")
    engine.step=scope(engine.step,"cosmos3_stage/engine_step")
    transformer=engine.entry.transformer
    transformer.encode_condition=scope(transformer.encode_condition,"cosmos3_stage/UND_encode")
    name,pixels,request,_,metadata=matrix["len65_97"]
    with profile(activities=[ProfilerActivity.CPU,ProfilerActivity.CUDA],record_shapes=True,with_stack=True) as prof:
        with record_function("cosmos3_dynamic_candidate/full_pixels_to_action/len31_to_len65_97"):
            output,row=measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
    ref=torch.load(a.reference/"actions"/(name+".pt"),map_location="cuda",weights_only=True)
    exact=bool(torch.equal(ref.contiguous().view(torch.uint8),output.contiguous().view(torch.uint8)))
    assert exact
    prof.export_chrome_trace(str(a.out/"candidate-dynamic.trace.json"))
    save(a.out/"profile-metadata.json",dict(complete=True,byte_equal=exact,workload=metadata,
        previous_workload="len31_17; two complete warmups",
        phase_counts=dict(counts),optimization=dict(control.last_request_stats),
        profiled_measurement_excluded_from_speedup=row,trace_kind="single candidate-only mapping/profile window"))
finally:
    if control is not None:control.close()
    engine.close()
