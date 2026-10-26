"""Exact, byte-verified GEN attention CSE added to v10 GEMM CSE.

The same-text fixture benefits; differing Q/K/V always fall back.
All eight transformer forwards and nonlinear operations execute.
Cache lifetime is exactly one CFG cond/uncond pair, never a request output.
"""
from pathlib import Path
import importlib.util,torch
_spec=importlib.util.spec_from_file_location('cosmos_round2_v11_parent',Path(__file__).with_name('candidate-round2-v10.py'))
_parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_parent)
version=_parent.version
def meta(t):return (tuple(t.shape),tuple(t.stride()),t.dtype,t.device)
class Control(_parent.Control):
 def __init__(self,transformer,vae,engine):
  self.attention_entries={};self.attention_bindings=[]
  self.attention_physical=0;self.attention_hits=0;self.attention_misses=0;self.attention_comparisons=0
  super().__init__(transformer,vae,engine)
  for index,(mod,old,fast) in enumerate(self.base.compact.bindings):
   def forward(q,k,v,attention_context=None,_index=index,_fast=fast):
    inputs=(q,k,v)
    eligible=(self.mode=='candidate' and self.phase in ('cond','uncond')
              and attention_context is None and all(t.is_cuda and t.dtype==torch.bfloat16 and t.ndim==4 for t in inputs))
    if not eligible:
     self.attention_physical+=1
     return _fast(q,k,v,attention_context)
    stream=torch.cuda.current_stream(q.device).cuda_stream
    if self.phase=='uncond':
     entry=self.attention_entries.pop(_index,None)
     if entry is not None:
      saved,result,versions,output_version,metadata,output_meta,saved_stream,nbytes=entry
      self.bytes-=nbytes
      valid=(stream==saved_stream and tuple(meta(t) for t in inputs)==metadata
             and tuple(version(t) for t in saved)==versions and version(result)==output_version and meta(result)==output_meta)
      if valid:
       equal=True
       for x,y in zip(inputs,saved):
        self.attention_comparisons+=1
        if not torch.equal(x.contiguous().view(torch.uint8),y.contiguous().view(torch.uint8)):
         equal=False;break
       if equal:
        self.attention_hits+=1
        return result
     self.attention_misses+=1;self.attention_physical+=1
     return _fast(q,k,v,attention_context)
    self.attention_physical+=1
    result=_fast(q,k,v,attention_context)
    if not isinstance(result,torch.Tensor):return result
    saved=tuple(t if version(t) is not None else t.clone() for t in inputs)
    result_saved=result if version(result) is not None else result.clone()
    nbytes=sum(t.numel()*t.element_size() for t in (*saved,result_saved))
    if _index not in self.attention_entries and self.bytes+nbytes<=self.cap:
     self.attention_entries[_index]=(saved,result_saved,tuple(version(t) for t in saved),version(result_saved),
         tuple(meta(t) for t in inputs),meta(result_saved),stream,nbytes)
     self.bytes+=nbytes;self.high_water_bytes=max(self.high_water_bytes,self.bytes)
    return result
   self.attention_bindings.append((mod,fast,forward))
  assert len(self.attention_bindings)==24,len(self.attention_bindings)
  self.set_mode('baseline')
 def clear(self):
  super().clear();self.attention_entries.clear()
 def set_mode(self,mode):
  super().set_mode(mode)
  if mode=='candidate':
   for mod,fast,wrapped in self.attention_bindings:mod.forward=wrapped
 def full(self,*args,**kwargs):
  before=(self.attention_physical,self.attention_hits,self.attention_misses,self.attention_comparisons)
  try:return super().full(*args,**kwargs)
  finally:
   physical=self.attention_physical-before[0];hits=self.attention_hits-before[1]
   self.last_request_stats.update(physical_gen_attention=physical,reused_gen_attention=hits,
       logical_gen_attention=physical+hits,attention_misses=self.attention_misses-before[2],
       attention_tensor_byte_comparisons=self.attention_comparisons-before[3],
       remaining_attention_entries=len(self.attention_entries))
def install(transformer,vae,engine):return Control(transformer,vae,engine)
