"""Screen only exact BF16 direct torch GEMM and packed down-projection weights."""
from pathlib import Path
import importlib.util,torch
from phyai.layers.linear.layers import LinearBase
_spec=importlib.util.spec_from_file_location("cosmos_linear_exact_rms_base",Path(__file__).with_name("candidate-v8.py"))
_base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_base)
class Control:
 def __init__(self,transformer,vae,engine):
  self.base=_base.install(transformer,vae,engine);self.bindings=[];self.calls=0;self.packed_bytes=0
  for name,mod in transformer.named_modules():
   if name.startswith("gen_layers.") and isinstance(mod,LinearBase):
    assert mod.bias is None and getattr(mod,"tp_size",1)==1
    old=mod.forward;original_b=mod.weight.t()
    packed_b=original_b.contiguous() if name.endswith(".mlp.down_proj") else original_b
    if packed_b is not original_b:self.packed_bytes+=packed_b.numel()*packed_b.element_size()
    def direct(x,_old=old,_b=original_b):
     if x.dtype!=torch.bfloat16 or not x.is_cuda:return _old(x)
     y=torch.mm(x.reshape(-1,x.shape[-1]),_b);self.calls+=1
     return y.reshape(*x.shape[:-1],_b.shape[1]),None
    def packed(x,_old=old,_b=packed_b):
     if x.dtype!=torch.bfloat16 or not x.is_cuda:return _old(x)
     y=torch.mm(x.reshape(-1,x.shape[-1]),_b);self.calls+=1
     return y.reshape(*x.shape[:-1],_b.shape[1]),None
    self.bindings.append((mod,old,direct,packed))
  assert len(self.bindings)==4*len(transformer.gen_layers)
  self.set_mode("official")
 def set_mode(self,mode):
  assert mode in ("official","combined_rms","combined_linear","combined_packed_linear")
  self.mode=mode;self.base.set_mode("combined_rms" if mode in ("combined_linear","combined_packed_linear") else mode)
  for mod,old,direct,packed in self.bindings:
   mod.forward=packed if mode=="combined_packed_linear" else direct if mode=="combined_linear" else old
 def full(self,*args,**kwargs):return self.base.full(*args,**kwargs)
 def close(self):
  for mod,old,direct,packed in self.bindings:mod.forward=old
  self.base.close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
