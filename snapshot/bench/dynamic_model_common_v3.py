"""Full GPU pixels -> VAE -> official engine.step -> GPU BF16 actions."""
from pathlib import Path
import argparse
import collections
import dataclasses
import functools
import hashlib
import importlib.util
import json
import os
import subprocess
import time
import torch

def parser():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--reference",type=Path)
    p.add_argument("--backend",choices=["official","candidate"],default="candidate")
    p.add_argument("--steps",type=int,default=4)
    p.add_argument("--cuda-graph",action="store_true")
    p.add_argument("--limit",type=int,default=0)
    p.add_argument("--pairs",type=int,default=6)
    p.add_argument("--case",action="append",default=[])
    return p

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,default=str)+"\n")

def emit(kind,**values):
    print(json.dumps(dict(kind=kind,time_ns=time.time_ns(),**values),default=str),flush=True)

def idle():
    raw=subprocess.check_output(["/usr/sbin/nvidia-smi","--query-compute-apps=pid,process_name","--format=csv,noheader"],text=True)
    other=[s for s in raw.splitlines() if s.strip() and int(s.split(",")[0])!=os.getpid()]
    if other: raise RuntimeError("Foreign GPU process: "+str(other))

def action_hash(value):
    return hashlib.sha256(value.cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()

def setup(a):
    idle();torch.set_grad_enabled(False);a.out.mkdir(parents=True,exist_ok=True)
    import phyai_kernel.jit_utils.compile as jit_compile
    jit_compile.PHYAI_KERNEL_CACHE_ROOT=Path(os.environ["COSMOS_TASK_ROOT"])/"cache/phyai_kernel"
    from phyai import Engine,EngineArgs
    from phyai.engine_config import DeviceConfig,EngineConfig,RuntimeConfig
    from phyai.models.cosmos3.main_cosmos3_policy import Cosmos3PolicyArgs
    from phyai.models.cosmos3 import Cosmos3WanVAE,Cosmos3WanVAEConfig,cosmos3_vae_weight_remap
    from phyai.models.cosmos3.model_runner_vae_cosmos3 import Cosmos3VAERunner
    from phyai.utils import load_config
    from phyai.weights import load_pretrained
    emit("load_start",backend=a.backend,pid=os.getpid())
    engine=Engine(EngineArgs(plugin="cosmos3_policy",
        plugin_args=Cosmos3PolicyArgs(checkpoint_dir=a.checkpoint,flow_shift=5.,use_karras_sigmas=False,decode_video=False),
        config=EngineConfig(device=DeviceConfig(target="cuda",params_dtype=torch.bfloat16),
            runtime=RuntimeConfig(use_cuda_graph=a.cuda_graph))))
    vae=Cosmos3WanVAE(load_config(a.checkpoint/"vae",Cosmos3WanVAEConfig))
    load_pretrained(vae,a.checkpoint/"vae",remap=cosmos3_vae_weight_remap,strict=False)
    vae=vae.to(device="cuda",dtype=torch.bfloat16).eval()
    vae_runner=Cosmos3VAERunner(vae,device="cuda",dtype=torch.bfloat16);vae_runner.setup()
    counts=collections.Counter()
    def wrap(obj,name,label):
        old=getattr(obj,name)
        @functools.wraps(old)
        def forward(*args,**kwargs):
            counts[label]+=1
            return old(*args,**kwargs)
        setattr(obj,name,forward)
    wrap(vae_runner,"encode","vae_encode")
    wrap(engine,"step","engine_step")
    wrap(engine.entry.transformer,"encode_condition","condition_encode")
    wrap(engine.entry.transformer,"forward","denoiser")
    save(a.out/"environment.json",dict(torch=torch.__version__,cuda=torch.version.cuda,
        gpu=torch.cuda.get_device_name(),capability=torch.cuda.get_device_capability(),
        source_revision=(Path(os.environ["COSMOS_SOURCE_ROOT"])/"REVISION").read_text().strip(),
        source_root=os.environ["COSMOS_SOURCE_ROOT"],checkpoint=str(a.checkpoint),dtype="BF16",
        runtime_cuda_graph=engine.entry.scheduler.runner.use_cuda_graph,pid=os.getpid(),
        boundary="GPU pixels -> VAE encode -> original engine.step (UND + 4x2 GEN + action head) -> ready GPU action",
        excluded=["checkpoint load","tokenization","pixel preprocessing","optional video decode","robot postprocessing"],
        operator_replacements=a.backend!="official",fixed_positive_equals_negative=False))
    emit("load_done",allocated_gib=torch.cuda.memory_allocated()/2**30)
    return engine,vae,vae_runner,counts

def install(engine,vae):
    task=Path(os.environ["COSMOS_TASK_ROOT"])
    spec=importlib.util.spec_from_file_location("cosmos_dynamic_entry",task/"solution/candidate-dynamic-v3.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.install(engine.entry.transformer,vae,engine)

def cases(a):
    from phyai.models.cosmos3 import Cosmos3ActionRequest,pixel_to_latent_shape
    rng=torch.Generator(device="cuda").manual_seed(42)
    images={}
    def image(frames=33,height=480,width=832,batch=1):
        key=(batch,frames,height,width)
        if key not in images:
            images[key]=torch.rand(batch,3,frames,height,width,device="cuda",dtype=torch.bfloat16,generator=rng)*2-1
        return images[key]
    def tokens(padded,real,offset,batch=1):
        ids=(torch.arange(padded,device="cuda",dtype=torch.long)%73+100+offset).unsqueeze(0).repeat(batch,1)
        mask=(torch.arange(padded,device="cuda")<real).long().unsqueeze(0).repeat(batch,1)
        return ids,mask
    rows=[]
    def add(name,pos,neg,*,real_pos=None,real_neg=None,offset=0,frames=33,height=480,width=832,action=32,batch=1,stream=False,same=False,flip=False,frames_cond=(0,)):
        ti,tm=tokens(pos,pos if real_pos is None else real_pos,offset,batch)
        ni,nm=(ti,tm) if same else tokens(neg,neg if real_neg is None else real_neg,offset+131,batch)
        req=Cosmos3ActionRequest(text_ids=ti,text_mask=tm,neg_text_ids=ni,neg_text_mask=nm,
            video_shape=pixel_to_latent_shape(frames,height,width),mode="policy",domain_id=8,
            action_chunk=action,raw_action_dim=10,action_dim=64,fps=15.,
            num_inference_steps=a.steps,guidance_scale=3.,seed=42,cond_frame_indexes=frames_cond)
        pixels=image(frames,height,width,batch)
        if flip:pixels=pixels.flip(-1)
        meta=dict(name=name,positive_padded=pos,positive_real=int(tm[0].sum().item()),
            negative_padded=neg,negative_real=int(nm[0].sum().item()),same_cfg=same,
            frames=frames,height=height,width=width,video_shape=list(req.video_shape),
            batch=batch,action_chunk=action,stream="nondefault" if stream else "default",
            fixture="deterministic varied synthetic token IDs; not a language/task rollout")
        rows.append((name,pixels,req,stream,meta))
    for name,p,n in [("len1_3",1,3),("len31_17",31,17),("len63_64",63,64),("len65_97",65,97),
                     ("len127_13",127,13),("len128_129",128,129),("len257_7",257,7)]:
        add(name,p,n)
    add("padded96_real31",96,64,real_pos=31,real_neg=17)
    add("same_shape_changed_ids",31,17,offset=17,flip=True)
    add("same_shape_changed_mask",96,64,real_pos=47,real_neg=29)
    add("return_len31_17",31,17)
    add("len65_nondefault_stream",65,97,stream=True)
    add("video320x512",33,18,height=320,width=512)
    add("video17frames",61,23,frames=17)
    add("action16",65,17,action=16)
    add("same_cfg_dynamic_query",47,47,height=320,width=512,same=True)
    add("batch2_official_fallback",11,7,frames=5,height=128,width=192,action=8,batch=2)
    add("long512",512,33)
    add("repeat_long512_warm",512,33)
    add("conditioning_frames0_2",67,19,frames_cond=(0,2))
    if a.case:rows=[r for r in rows if r[0] in a.case]
    if a.limit:rows=rows[:a.limit]
    save(a.out/"workload-cases.json",[r[-1] for r in rows])
    return rows

def run_full(control,pixels,request,vae_runner,engine):
    if control is not None:return control.full(pixels,request,vae_runner,engine)
    latent=vae_runner.encode(pixels)
    return engine.step(dataclasses.replace(request,cond_video_latents=latent))

def measured(fn,counts,request):
    idle();torch.cuda.synchronize();counts.clear()
    start,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
    start.record();begin=time.perf_counter()
    output=fn();submitted=time.perf_counter()
    end.record();end.synchronize();ready=time.perf_counter()
    row=dict(event_ms=start.elapsed_time(end),ready_wall_ms=(ready-begin)*1000,
        host_submit_ms=(submitted-begin)*1000,phase_counts=dict(counts),
        output_shape=list(output.shape),output_dtype=str(output.dtype),action_sha256=action_hash(output))
    assert counts["vae_encode"]==1 and counts["engine_step"]==1,row
    assert counts["denoiser"]==request.num_inference_steps*2,row
    assert output.dtype==torch.bfloat16 and torch.isfinite(output).all(),row
    assert list(output.shape)==[request.text_ids.shape[0],request.action_chunk,request.raw_action_dim],row
    return output,row
