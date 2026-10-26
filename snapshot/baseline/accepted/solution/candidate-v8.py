"""Preserve BF16 residual rounding and official RMSNorm reduction layout."""
from pathlib import Path
import importlib.util
from rounded_add_rmsnorm_v1 import rounded_add_rmsnorm
_spec=importlib.util.spec_from_file_location("cosmos_round_norm_base",Path(__file__).with_name("candidate.py"))
_base=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_base)
class Control:
 def __init__(self,transformer,vae,engine):
  self.base=_base.install(transformer,vae,engine);self.bindings=[];self.calls=0
  for i,layer in enumerate(transformer.gen_layers):
   for norm in (layer.input_layernorm,layer.post_attention_layernorm):
    assert norm.variant=="rms" and not norm.cast_before_affine
   old=layer.forward;last=(i==len(transformer.gen_layers)-1)
   def forward(hidden_states,k_und,v_und,freqs_cos,freqs_sin,attention_context=None,attention_preparation=None,_layer=layer,_last=last):
    if isinstance(hidden_states,tuple):
     h,res=hidden_states
     residual,hidden_states=rounded_add_rmsnorm(h,res,_layer.input_layernorm.weight,_layer.input_layernorm.variance_epsilon);self.calls+=1
    else:
     residual=hidden_states
     hidden_states=_layer.input_layernorm(hidden_states)
    hidden_states=_layer.cross_attention(hidden_states,k_und,v_und,freqs_cos,freqs_sin,attention_context,attention_preparation)
    residual,hidden_states=rounded_add_rmsnorm(hidden_states,residual,_layer.post_attention_layernorm.weight,_layer.post_attention_layernorm.variance_epsilon);self.calls+=1
    out=_layer.mlp(hidden_states)
    return residual+out if _last else (out,residual)
   self.bindings.append((layer,old,forward))
  self.set_mode("official")
 def set_mode(self,mode):
  assert mode in ("official","combined","combined_rms")
  self.mode=mode;self.base.set_mode("combined" if mode=="combined_rms" else mode)
  for layer,old,new in self.bindings:layer.forward=new if mode=="combined_rms" else old
 def full(self,*args,**kwargs):return self.base.full(*args,**kwargs)
 def close(self):
  for layer,old,new in self.bindings:layer.forward=old
  self.base.close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
