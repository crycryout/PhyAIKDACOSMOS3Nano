"""Compact v19 output with immutable attention-v12 retained for baseline mode."""
from pathlib import Path
import functools,os
import torch,flashinfer,tvm_ffi.cpp
from flashinfer.jit import env as e
@functools.cache
def extension():
 task=Path(os.environ['COSMOS_TASK_ROOT'])
 inc=[*e.CCCL_INCLUDE_DIRS,e.FLASHINFER_INCLUDE_DIR,e.FLASHINFER_CSRC_DIR,*e.CUTLASS_INCLUDE_DIRS,e.FLASHINFER_INCLUDE_DIR/'flashinfer/attention/blackwell',e.FLASHINFER_INCLUDE_DIR/'flashinfer/attention/blackwell/collective']
 return tvm_ffi.cpp.load(name='cosmos_cutlass_compact_v19',build_directory=str(task/'cache/tvm-ffi/cosmos_cutlass_compact_v19'),sources=[str(task/'solution/cutlass_compact_v19.cu')],extra_include_paths=[str(x) for x in inc],extra_cuda_cflags=['-O3','-lineinfo','-arch=sm_110a','-use_fast_math','--expt-relaxed-constexpr','-DFLASHINFER_ENABLE_BF16','-DFLASHINFER_ENABLE_F16'])
class CompactAttention:
 def __init__(self,transformer):
  self.bindings=[];self.plans={};self.calls=0
  for layer in transformer.gen_layers:
   mod=layer.cross_attention.attn;old=mod.forward
   def forward(q,k,v,attention_context=None,_old=old):
    if q.ndim!=4 or q.shape[0]!=1 or q.shape[-2:]!=(32,128) or k.shape[-2:]!=(8,128) or q.dtype!=torch.bfloat16:
     return _old(q,k,v,attention_context)
    qs,ks,vs=q.squeeze(0),k.squeeze(0),v.squeeze(0)
    stream=torch.cuda.current_stream(q.device).cuda_stream
    key=(tuple(qs.shape),tuple(ks.shape),qs.dtype,qs.device,stream)
    if key not in self.plans:
     workspace=torch.empty(128*1024*1024,device=qs.device,dtype=torch.uint8)
     wrapper=flashinfer.BatchPrefillWithRaggedKVCacheWrapper(workspace,kv_layout='NHD',backend='cutlass')
     qo=torch.tensor([0,qs.shape[0]],device=qs.device,dtype=torch.int32);kv=torch.tensor([0,ks.shape[0]],device=qs.device,dtype=torch.int32)
     wrapper.plan(qo,kv,qs.shape[1],ks.shape[1],qs.shape[2],causal=False,sm_scale=1/(qs.shape[-1]**.5),q_data_type=qs.dtype,kv_data_type=ks.dtype)
     self.plans[key]=(wrapper,workspace,qo,kv)
    wrapper,workspace,qo,kv=self.plans[key]
    ve=torch.ones((*vs.shape[:-1],192),device=vs.device,dtype=vs.dtype);ve[...,:128].copy_(vs)
    out=torch.empty((*qs.shape[:-1],128),device=qs.device,dtype=qs.dtype)
    extension().run(workspace,qs,ks,ve,qo,kv,*wrapper._plan_info,out,None,0,1/(qs.shape[-1]**.5),1.,1.,1.,1.,qs.shape[0])
    self.calls+=1
    return out.unsqueeze(0)
   self.bindings.append((mod,old,forward))
 def enable(self):
  for mod,old,forward in self.bindings:mod.forward=forward
 def restore(self):
  for mod,old,forward in self.bindings:mod.forward=old
