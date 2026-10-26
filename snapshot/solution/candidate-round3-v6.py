"""v6 hypothesis: official precision-preserving torch.compile for eager preparation.

Graph remains off. Baseline still runs the original eager helper. Candidate
physical preparation uses the same official emulate_precision_casts option;
model byte gates and audit-mode eager comparisons are required before use.
"""
from pathlib import Path
import importlib.util,torch
from torch._dynamo.exc import FailOnRecompileLimitHit
_spec=importlib.util.spec_from_file_location('cosmos_r3_fused_eager_parent',Path(__file__).with_name('candidate-round3-v5.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.compiled_preparation=None;self.compile_fallback=False;self.audit_fused_preparation=False
  self.fused_invocations=0;self.fused_audits=0;self.fused_fallbacks=0
  super().__init__(transformer,vae,engine)
  self.compiled_preparation=torch.compile(self.original_eager,fullgraph=True,dynamic=True,
     options={'emulate_precision_casts':True,'triton.cudagraphs':False})
  def physical(*args,**kwargs):
   self.fused_invocations+=1
   if self.compile_fallback:
    self.fused_fallbacks+=1;result=self.original_eager(*args,**kwargs)
   else:
    try:result=self.compiled_preparation(*args,**kwargs)
    except FailOnRecompileLimitHit:
     self.compile_fallback=True;self.fused_fallbacks+=1;result=self.original_eager(*args,**kwargs)
   if self.audit_fused_preparation:
    eager=self.original_eager(*args,**kwargs)
    assert parent.parent.parent.parent.byte_equal(result,eager),'Fused preparation differs from eager BF16 bytes'
    self.fused_audits+=1
   return result
  self.physical_preparation=physical
 def pure_call(self,key,fn,args,kwargs):
  if key[0]=='attention_prepare_eager' and self.mode=='candidate':
   fn=self.physical_preparation
  return super().pure_call(key,fn,args,kwargs)
 def signature(self,*args,**kwargs):
  return super().signature(*args,**kwargs)+(id(self.compiled_preparation),self.compile_fallback)
 def full(self,*args,**kwargs):
  before=(self.fused_invocations,self.fused_audits,self.fused_fallbacks)
  try:return super().full(*args,**kwargs)
  finally:
   self.last_request_stats['fused_eager_preparation']=dict(invocations=self.fused_invocations-before[0],
       explicit_eager_byte_audits=self.fused_audits-before[1],fallbacks=self.fused_fallbacks-before[2],
       fallback_active=self.compile_fallback,cuda_graph=False,emulate_precision_casts=True,
       physical_call_counts_include_audit_recomputations=True)
def install(transformer,vae,engine):return Control(transformer,vae,engine)
