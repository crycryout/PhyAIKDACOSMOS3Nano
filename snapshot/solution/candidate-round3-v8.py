"""v8: v7 plus exact PV144 attention, with frozen R2-v12 baseline dispatch.

Only the compiled physical attention kernel changes in candidate mode.
All module forwards, pair-scoped CSE lifetime, dtype and timing boundaries
are inherited unchanged. Baseline mode calls the original compact-v13 loader.
"""
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location('cosmos_r3_v8_parent',Path(__file__).with_name('candidate-round3-v7.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
_route_spec=importlib.util.spec_from_file_location('cosmos_r3_pv144_loader',Path(__file__).with_name('compact_attention_route_v35.py'))
route=importlib.util.module_from_spec(_route_spec);_route_spec.loader.exec_module(route)
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.attention_namespace=None
  self.v13_dispatches=0;self.pv144_dispatches=0
  super().__init__(transformer,vae,engine)
  bindings=self.frozen.base.compact.bindings
  namespace=bindings[0][2].__globals__
  assert all(fast.__globals__ is namespace for mod,old,fast in bindings)
  self.original_extension=namespace['extension']
  self.pv144_extension=route.extension()
  def extension():
   if self.mode=='candidate':
    self.pv144_dispatches+=1
    return self.pv144_extension
   self.v13_dispatches+=1
   return self.original_extension()
  self.dispatched_extension=extension
  self.attention_namespace=namespace
  namespace['extension']=extension
 def signature(self,*args,**kwargs):
  result=super().signature(*args,**kwargs)
  if self.attention_namespace is None:return result
  return result+(parent.parent.function_id(self.attention_namespace['extension']),id(self.pv144_extension))
 def full(self,*args,**kwargs):
  before=(self.v13_dispatches,self.pv144_dispatches)
  try:return super().full(*args,**kwargs)
  finally:
   self.last_request_stats['physical_attention_kernel']=dict(
    baseline='cutlass_compact_v13',candidate='cutlass_compact_v35',
    baseline_dispatches=self.v13_dispatches-before[0],
    candidate_dispatches=self.pv144_dispatches-before[1],
    active_pv_columns=144,abi_v_columns=192,
    all_module_forwards_execute=True)
 def close(self):
  if self.attention_namespace is not None:self.attention_namespace['extension']=self.original_extension
  super().close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
