"""v11: validated v9 plus exact PV144 correction with numerator32 TMEM tiles.

Only the candidate physical attention extension changes. The inherited closure
reads self.pv144_extension each dispatch; baseline continues using original v13.
All forward calls, native proof guards and pair-scoped CSE are unchanged.
"""
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location('cosmos_r3_v11_parent',Path(__file__).with_name('candidate-round3-v9.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
_route_spec=importlib.util.spec_from_file_location('cosmos_r3_pv144_v40_loader',Path(__file__).with_name('compact_attention_route_v40.py'))
route=importlib.util.module_from_spec(_route_spec);_route_spec.loader.exec_module(route)
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  super().__init__(transformer,vae,engine)
  self.pv144_extension=route.extension()
 def full(self,*args,**kwargs):
  try:return super().full(*args,**kwargs)
  finally:
   stats=self.last_request_stats['physical_attention_kernel']
   stats['candidate']='cutlass_compact_v40'
   stats['correction_numerator_tile_columns']=32
   stats['correction_denominator_tile_columns']=16
def install(transformer,vae,engine):return Control(transformer,vae,engine)
