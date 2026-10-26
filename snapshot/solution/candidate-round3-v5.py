"""v5: hook the actual eager RoPE/KV helper used when CUDA Graph is off.

v3/v4's runner-fusion wrapper is unreachable in this fixed Graph-off route.
This version adds only eager pure-operator CSE; all real module forwards run.
The native CPU-signature experiment remains independent and is not imported.
"""
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location('cosmos_r3_eager_parent',Path(__file__).with_name('candidate-round3-v4.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.eager_namespace=None
  super().__init__(transformer,vae,engine)
  namespace=transformer.gen_layers[0].cross_attention.forward.__globals__
  assert all(layer.cross_attention.forward.__globals__ is namespace for layer in transformer.gen_layers)
  self.eager_namespace=namespace
  self.original_eager=namespace['prepare_cosmos3_attention']
  def prepare(*args,**kwargs):
   self.enter_pure_phase()
   index=self.pure_counts['attention_prepare_eager'];self.pure_counts['attention_prepare_eager']+=1
   return self.pure_call(('attention_prepare_eager',index),self.original_eager,args,kwargs)
  self.reused_eager=prepare
  self.set_mode('baseline')
 def signature(self,*args,**kwargs):
  result=super().signature(*args,**kwargs)
  return result+(parent.function_id(self.original_eager),
                 parent.function_id(self.eager_namespace['prepare_cosmos3_attention']))
 def set_mode(self,mode):
  super().set_mode(mode)
  if self.eager_namespace is not None:
   self.eager_namespace['prepare_cosmos3_attention']=self.reused_eager if mode=='candidate' else self.original_eager
 def full(self,*args,**kwargs):
  fields=('logical','physical','reused','fallback','audit_recomputations')
  before={field:self.pure_counters[('attention_prepare_eager',field)] for field in fields}
  try:return super().full(*args,**kwargs)
  finally:
   self.last_request_stats['pure_operator_reuse']['by_kind']['attention_prepare_eager']={field:self.pure_counters[('attention_prepare_eager',field)]-before[field] for field in fields}
   self.last_request_stats['preparation_dispatch']=dict(route='actual eager prepare_cosmos3_attention helper',cuda_graph=False,runner_fusion_is_unused=True,all_module_forwards_execute=True)
 def close(self):
  if self.eager_namespace is not None:self.eager_namespace['prepare_cosmos3_attention']=self.original_eager
  super().close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
