"""v7: pair-scoped fusion-preparation CSE on the actual accepted R2 route.

The accepted R1 parent enables compiled preparation independently of Graph
capture. v5's added eager hook is unused. Keep the verified v4 numerical
operations and guard both live preparation methods against route mutation.
"""
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location('cosmos_r3_actual_fusion_parent',Path(__file__).with_name('candidate-round3-v4.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.helper_namespace=None
  super().__init__(transformer,vae,engine)
  self.helper_namespace=transformer.gen_layers[0].cross_attention.forward.__globals__
 def signature(self,*args,**kwargs):
  result=super().signature(*args,**kwargs)
  return result+(parent.function_id(self.prepare_provider.prepare),
                 parent.function_id(self.prepare_provider.forward),
                 parent.function_id(self.helper_namespace['prepare_cosmos3_attention']))
 def full(self,*args,**kwargs):
  try:return super().full(*args,**kwargs)
  finally:
   counts=self.last_request_stats['pure_operator_reuse']['by_kind']['attention_prepare']
   self.last_request_stats['preparation_dispatch']=dict(
      runtime_cuda_graph=bool(self.frozen.runner.use_cuda_graph),
      counted_route='runner Fusion.forward; accepted parent enables fusion without Graph',
      logical=counts['logical'],physical=counts['physical'],reused=counts['reused'],
      audit_recomputations=counts['audit_recomputations'],
      eager_helper_intercepted=False,all_module_forwards_execute=True)
def install(transformer,vae,engine):return Control(transformer,vae,engine)
