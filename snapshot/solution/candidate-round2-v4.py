from cublaslt_route_v2 import Control as LinearControl
from compact_attention_dynamic_v2 import CompactAttention
class Control:
 def __init__(self,transformer,vae,engine):
  self.linear=LinearControl(transformer,vae,engine)
  self.base=self.linear.base
  self.compact=CompactAttention(transformer)
  self.set_mode('baseline')
 @property
 def calls(self):return self.linear.calls
 def set_mode(self,mode):
  self.linear.set_mode(mode);self.mode=mode
  if mode=='candidate':self.compact.enable()
 def full(self,*args,**kwargs):return self.linear.full(*args,**kwargs)
 def close(self):
  self.compact.restore();self.linear.close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
