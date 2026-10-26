"""v3: exact pair-scoped CSE for stateless RoPE and KV preparation.

All original transformer, attention-module and MLP-module forwards still run.
The added cache stores one pure preparation operator's outputs per layer,
only until the matching unconditional call in the same denoise step.
"""
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location('cosmos_r3_prepare_parent',Path(__file__).with_name('candidate-round3-v2.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.prepare_provider=None
  super().__init__(transformer,vae,engine)
  self.prepare_provider=engine.entry.scheduler.runner._attention_fusion
  self.original_preparation=self.prepare_provider.forward
  def prepare(*args,**kwargs):
   self.enter_pure_phase()
   index=self.pure_counts['attention_prepare'];self.pure_counts['attention_prepare']+=1
   return self.pure_call(('attention_prepare',index),self.original_preparation,args,kwargs)
  self.reused_preparation=prepare
  self.set_mode('baseline')
 def signature(self,*args,**kwargs):
  provider=self.prepare_provider
  return super().signature(*args,**kwargs)+(provider.enabled,id(provider._compiled),provider._recompile_limit_hit,parent.parent.function_id(self.original_preparation))
 def set_mode(self,mode):
  super().set_mode(mode)
  if self.prepare_provider is not None:
   self.prepare_provider.forward=self.reused_preparation if mode=='candidate' else self.original_preparation
 def full(self,*args,**kwargs):
  fields=('logical','physical','reused','fallback','audit_recomputations')
  before={field:self.pure_counters[('attention_prepare',field)] for field in fields}
  try:return super().full(*args,**kwargs)
  finally:
   self.last_request_stats['pure_operator_reuse']['by_kind']['attention_prepare']={field:self.pure_counters[('attention_prepare',field)]-before[field] for field in fields}
 def close(self):
  if self.prepare_provider is not None:self.prepare_provider.forward=self.original_preparation
  super().close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
