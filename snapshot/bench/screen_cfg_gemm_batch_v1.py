"""Feasibility only: batch the two actual CFG GEMM inputs without skipping either."""
from dynamic_model_common_full_v3 import *
import ctypes
import statistics
a=parser().parse_args()
assert a.reference is not None
engine,vae,vae_runner,counts=setup(a)
control=None
doc=dict(complete=False,screen_only=True,full_model_candidate=False,rows=[])
try:
    control=install(engine,vae)
    linear=control.frozen.base.linear
    by_id={id(mod):(fast,fast.__defaults__[1]) for mod,old,fast in linear.bindings}
    captured={};hooks=[]
    for name,mod in engine.entry.transformer.named_modules():
        if not name.startswith("gen_layers.0.") or id(mod) not in by_id:continue
        category=name.split(".",2)[2].replace(".","_")
        def capture(mod,args,result,_category=category):
            values=captured.setdefault(_category,[])
            if len(values)<2:
                values.append((args[0].detach().clone().reshape(-1,args[0].shape[-1]),
                               result[0].detach().clone().reshape(-1,result[0].shape[-1])))
        hooks.append(mod.register_forward_hook(capture))
    matrix=cases(a);assert len(matrix)==1
    name,pixels,request,use_stream,metadata=matrix[0]
    assert not use_stream and not metadata["same_cfg"]
    try:
        engine.entry.scheduler.runner.reset();engine.entry.scheduler.runner._condition_cache.clear()
        output,model_row=measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
        ref=torch.load(a.reference/"actions"/(name+".pt"),map_location="cuda",weights_only=True)
        assert torch.equal(output.contiguous().view(torch.uint8),ref.contiguous().view(torch.uint8))
    finally:
        for hook in hooks:hook.remove()
    lib=linear.lib;P,I,S=ctypes.c_void_p,ctypes.c_int,ctypes.c_size_t
    for fname,args,ret in [("lt_count",[P],I),("lt_attr_full",[P,I,I],I)]:
        fn=getattr(lib,fname);fn.argtypes=args;fn.restype=ret
    workspace=torch.empty(64*1024*1024,device="cuda",dtype=torch.uint8)
    stream=torch.cuda.current_stream().cuda_stream
    def eq(x,y):return bool(torch.equal(x.contiguous().view(torch.uint8),y.contiguous().view(torch.uint8)))
    def timed(fn):
        begin,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
        begin.record();fn();end.record();end.synchronize();return begin.elapsed_time(end)
    for category,values in captured.items():
        idle();assert len(values)==2
        fast,weight=next(by_id[id(mod)] for pname,mod in engine.entry.transformer.named_modules()
                         if pname=="gen_layers.0."+category.replace("cross_attention_","cross_attention.").replace("mlp_","mlp."))
        x0,y0=values[0];x1,y1=values[1]
        assert x0.shape==x1.shape
        x=torch.cat((x0,x1));reference=torch.cat((y0,y1))
        m,k=x.shape;n=weight.shape[1]
        row=dict(category=category,source_M=x0.shape[0],merged_shape=[m,n,k],
                 source_input_bytes_equal=eq(x0,x1),candidates=[])
        doc["rows"].append(row)
        def separate():
            fast(x0);fast(x1)
        def merged_torch():return torch.mm(torch.cat((x0,x1)),weight)
        row["torch_merged_bytes_equal"]=eq(merged_torch(),reference)
        for _ in range(3):separate();merged_torch()
        row["separate_inherited_ms"]=statistics.median(timed(separate) for _ in range(7))
        row["torch_merged_including_cat_ms"]=statistics.median(timed(merged_torch) for _ in range(7))
        row["torch_ratio"]=row["torch_merged_including_cat_ms"]/row["separate_inherited_ms"]
        plan=lib.lt_make(m,n,k,int(weight.stride(-1)==1),workspace.numel(),64)
        try:
            out=torch.empty_like(reference)
            def run(index,value=x):
                rc=lib.lt_run(plan,index,value.data_ptr(),weight.data_ptr(),out.data_ptr(),
                              workspace.data_ptr(),workspace.numel(),stream)
                if rc:raise RuntimeError((category,index,rc))
            coarse=[]
            for index in range(lib.lt_count(plan)):
                try:coarse.append((timed(lambda:run(index)),index))
                except RuntimeError as error:row["candidates"].append(dict(index=index,error=str(error)))
            changed=torch.randn(x.shape,device=x.device,dtype=x.dtype,
                                generator=torch.Generator(device="cuda").manual_seed(271828))
            fixtures=[("actual_two_cfg",x,reference),("changed",changed,torch.mm(changed,weight)),
                      ("zero",torch.zeros_like(x),torch.zeros_like(reference))]
            for _,index in sorted(coarse)[:12]:
                entry=dict(index=index,attrs={str(j):lib.lt_attr_full(plan,index,j) for j in range(9)},byte_checks={})
                row["candidates"].append(entry)
                for label,value,expected in fixtures:
                    out.fill_(float("nan"));run(index,value);torch.cuda.synchronize()
                    entry["byte_checks"][label]=eq(out,expected)
                    if not entry["byte_checks"][label]:break
                entry["all_bytes_equal"]=len(entry["byte_checks"])==3 and all(entry["byte_checks"].values())
                if entry["all_bytes_equal"]:
                    entry["median_ms"]=statistics.median(timed(lambda:run(index)) for _ in range(7))
                    entry["ratio_to_two_inherited"]=entry["median_ms"]/row["separate_inherited_ms"]
                save(a.out/"cfg-gemm-batch-screen.json",doc)
            good=[e for e in row["candidates"] if e.get("all_bytes_equal")]
            row["best_lt"]=min(good,key=lambda e:e["median_ms"]) if good else None
            emit("cfg_batch_gemm_screen",**{k:v for k,v in row.items() if k!="candidates"})
            save(a.out/"cfg-gemm-batch-screen.json",doc)
        finally:lib.lt_free(plan)
    doc.update(complete=True,source_model_byte_equal=True,source_workload=metadata,source_model_measurement=model_row)
    save(a.out/"cfg-gemm-batch-screen.json",doc)
finally:
    if control is not None:control.close()
    engine.close()
