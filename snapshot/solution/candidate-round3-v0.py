"""Third-round baseline is R2-v12 in candidate mode, never its old baseline mode."""
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location('cosmos_round3_frozen_r2',Path(__file__).with_name('candidate-round2-v12.py'))
r2=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(r2)
class Control:
 def __init__(self,transformer,vae,engine):
  self.frozen=r2.install(transformer,vae,engine);self.set_mode('baseline')
 @property
 def calls(self):return self.frozen.calls
 @property
 def last_request_stats(self):return self.frozen.last_request_stats
 @property
 def attention_bindings(self):return self.frozen.attention_bindings
 def set_mode(self,mode):
  assert mode in ('baseline','candidate');self.mode=mode
  self.frozen.set_mode('candidate')
 def full(self,*args,**kwargs):return self.frozen.full(*args,**kwargs)
 def close(self):self.frozen.close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
