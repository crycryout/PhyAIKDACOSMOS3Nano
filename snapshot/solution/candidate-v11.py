"""Screen-only exact BF16 attention + exact residual RMS + causal VAE prefix."""
from pathlib import Path
import importlib.util,functools,os
import torch,flashinfer,tvm_ffi.cpp
from flashinfer.jit import env as e
_spec=importlib.util.spec_from_file_location("cosmos_exact_attention_base",Path(__file__).with_name("candidate-v10.py"))
_base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_base)
@functools.cache
def extension():
 task=Path(os.environ["COSMOS_TASK_ROOT"])
 inc=[*e.CCCL_INCLUDE_DIRS,e.FLASHINFER_INCLUDE_DIR,e.FLASHINFER_CSRC_DIR,*e.CUTLASS_INCLUDE_DIRS,e.FLASHINFER_INCLUDE_DIR/"flashinfer/attention/blackwell",e.FLASHINFER_INCLUDE_DIR/"flashinfer/attention/blackwell/collective"]
 return tvm_ffi.cpp.load(name="cosmos_cutlass_kv64_rounded_p_v12",build_directory=str(task/"cache/tvm-ffi/cosmos_cutlass_kv64_rounded_p_v12"),sources=[str(task/"solution/cutlass_kv64_rounded_p_v12.cu")],extra_include_paths=[str(x) for x in inc],extra_cuda_cflags=["-O3","-lineinfo","-arch=sm_110a","-use_fast_math","--expt-relaxed-constexpr","-DFLASHINFER_ENABLE_BF16","-DFLASHINFER_ENABLE_F16"])
class Control:
 def __init__(self,transformer,vae,engine):
  self.base=_base.install(transformer,vae,engine);self.bindings=[];self.plans={};self.calls=0
  for layer in transformer.gen_layers:
   mod=layer.cross_attention.attn;old=mod.forward
   def forward(q,k,v,attention_context=None,_old=old):
    if q.ndim!=4 or q.shape[0]!=1 or q.shape[-2:]!=(32,128) or k.shape[-2:]!=(8,128) or q.dtype!=torch.bfloat16:
     return _old(q,k,v,attention_context)
    qs,ks,vs=q.squeeze(0),k.squeeze(0),v.squeeze(0)
    key=(tuple(qs.shape),tuple(ks.shape),qs.dtype,qs.device)
    if key not in self.plans:
     workspace=torch.empty(128*1024*1024,device=qs.device,dtype=torch.uint8)
     wrapper=flashinfer.BatchPrefillWithRaggedKVCacheWrapper(workspace,kv_layout="NHD",backend="cutlass")
     qo=torch.tensor([0,qs.shape[0]],device=qs.device,dtype=torch.int32)
     kv=torch.tensor([0,ks.shape[0]],device=qs.device,dtype=torch.int32)
     wrapper.plan(qo,kv,qs.shape[1],ks.shape[1],qs.shape[2],causal=False,sm_scale=1/(qs.shape[-1]**.5),q_data_type=qs.dtype,kv_data_type=ks.dtype)
     self.plans[key]=(wrapper,workspace,qo,kv)
    wrapper,workspace,qo,kv=self.plans[key]
    ve=torch.ones((*vs.shape[:-1],192),device=vs.device,dtype=vs.dtype)
    ve[...,:128].copy_(vs)
    out=torch.empty((*qs.shape[:-1],256),device=qs.device,dtype=qs.dtype)
    extension().run(workspace,qs,ks,ve,qo,kv,*wrapper._plan_info,out,None,0,1/(qs.shape[-1]**.5),1.,1.,1.,1.,qs.shape[0])
    self.calls+=1
    return out[...,:128].contiguous().unsqueeze(0)
   self.bindings.append((mod,old,forward))
  self.set_mode("official")
 def set_mode(self,mode):
  assert mode in ("official","combined_rms","combined_linear","combined_packed_linear","combined_exact","combined_packed_exact")
  self.mode=mode;self.base.set_mode("combined_packed_linear" if mode=="combined_packed_exact" else "combined_rms" if mode=="combined_exact" else mode)
  for mod,old,new in self.bindings:mod.forward=new if mode in ("combined_exact","combined_packed_exact") else old
 def full(self,*args,**kwargs):return self.base.full(*args,**kwargs)
 def close(self):
  for mod,old,new in self.bindings:mod.forward=old
  self.base.close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
