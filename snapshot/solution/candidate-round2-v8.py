"""Internal CFG gate batching with all eight logical denoisers retained."""
from pathlib import Path
import os,ctypes,dataclasses,json,importlib.util
import torch
from phyai.layers.linear.layers import LinearBase
from phyai.models.cosmos3.modeling_cosmos3 import DomainAwareLinear
from cublaslt_route_v4 import library
_spec=importlib.util.spec_from_file_location('cosmos_round2_cfg_base',Path(__file__).with_name('candidate-round2-v6.py'))
_mod=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_mod)
class Control:
 def __init__(self,transformer,vae,engine):
  self.base=_mod.install(transformer,vae,engine);self.transformer=transformer
  self.runner=engine.entry.scheduler.runner;self.old_forward=self.runner.forward
  self.gate_calls=0;self.logical_denoisers=0;self.physical_pairs=0;self.pending=None;self.request=None
  self.lib=library();self.plans={};self.workspaces={};self.extra=[];self.base.set_mode('candidate')
  self.gen_ids={id(m) for name,m in transformer.named_modules() if name.startswith('gen_layers.') and isinstance(m,LinearBase)}
  task=Path(os.environ['COSMOS_TASK_ROOT'])
  selected=json.loads((task/'solution/cublaslt-selected-cfg-v1.json').read_text())['configurations']['mlp_gate_up_proj']
  for name,m in transformer.named_modules():
   if isinstance(m,LinearBase):
    old=m.forward
    if name.startswith('gen_layers.') and name.endswith('mlp.gate_up_proj'):
     packed=m.weight.t().contiguous()
     def new(x,*args,_old=old,_b=packed,**kw):
      if x.shape[0]!=2 or x.numel()//x.shape[-1]!=7084:return _old(x,*args,**kw)
      aa=x.reshape(-1,x.shape[-1]);stream=torch.cuda.current_stream(aa.device).cuda_stream
      key=(aa.device.index,stream)
      if key not in self.plans:
       ws=torch.empty(64*1024*1024,device=aa.device,dtype=torch.uint8)
       plan=self.lib.lt_make_view(7084,_b.shape[1],aa.shape[1],1,1,ws.numel(),1)
       attrs=(ctypes.c_int*9)(*[selected['attrs'][str(z)] for z in range(9)])
       idx=self.lib.lt_configure(plan,attrs,ws.numel());assert idx>=0,idx
       self.plans[key]=(plan,idx,ws)
      plan,idx,ws=self.plans[key];out=torch.empty((7084,_b.shape[1]),device=aa.device,dtype=aa.dtype)
      rc=self.lib.lt_run(plan,idx,_b.data_ptr(),aa.data_ptr(),out.data_ptr(),ws.data_ptr(),ws.numel(),stream);assert rc==0,rc
      self.gate_calls+=1;return out.reshape(*x.shape[:-1],_b.shape[1]),None
    else:
     def new(x,*args,_old=old,**kw):
      if x.ndim>1 and x.shape[0]==2:
       values=[_old(x[i:i+1],*args,**kw) for i in range(2)]
       return torch.cat([v[0] for v in values],dim=0),values[0][1]
      return _old(x,*args,**kw)
    self.extra.append((m,old,new))
   elif isinstance(m,DomainAwareLinear):
    old=m.forward
    def new(x,domain,*args,_old=old,**kw):
     if x.shape[0]==2:return torch.cat([_old(x[i:i+1],domain[i:i+1],*args,**kw) for i in range(2)],dim=0)
     return _old(x,domain,*args,**kw)
    self.extra.append((m,old,new))
  for layer in transformer.gen_layers:
   m=layer.cross_attention.attn;old=m.forward
   def new(q,k,v,attention_context=None,_old=old):
    if q.shape[0]==2:return torch.cat([_old(q[i:i+1],k[i:i+1],v[i:i+1],None) for i in range(2)],dim=0)
    return _old(q,k,v,attention_context)
   self.extra.append((m,old,new))
  def paired(branch,hidden_states,timestep,**kw):
   if self.mode!='candidate' or self.request is None or self.request.guidance_scale<=1:return self.old_forward(branch,hidden_states,timestep,**kw)
   if branch=='uncond':
    assert self.pending is not None
    signature,result=self.pending;self.pending=None
    assert signature==(id(hidden_states),id(timestep),id(kw.get('action_latents')))
    return result
   assert branch=='cond' and hidden_states.shape[0]==1 and self.pending is None
   shape=kw['video_shape'];fps=kw.get('fps');alen=kw['action_latents'].shape[1]
   c=self.runner.condition('cond',kw['text_ids'],kw['text_mask'],shape,fps,action_len=alen)
   u=self.runner.condition('uncond',self.request.neg_text_ids,self.request.neg_text_mask,shape,fps,action_len=alen)
   assert c.video_shape==u.video_shape and c.action_len==u.action_len
   joined=dataclasses.replace(c,cached_kv=[(torch.cat([ck,uk],0),torch.cat([cv,uv],0)) for (ck,cv),(uk,uv) in zip(c.cached_kv,u.cached_kv,strict=True)],freqs_gen=tuple(torch.cat([ct,ut],0) for ct,ut in zip(c.freqs_gen,u.freqs_gen,strict=True)),attention_contexts=None,attention_preparation=None)
   inputs={name:torch.cat([value,value],0) if isinstance(value,torch.Tensor) else value for name,value in kw.items() if name in ('noisy_frame_mask','action_latents','action_domain_id','action_noisy_mask','sound_latents','sound_noisy_mask')}
   result=self.transformer(torch.cat([hidden_states,hidden_states],0),torch.cat([timestep,timestep],0),joined,**inputs)
   assert isinstance(result,tuple) and all(v.shape[0]==2 for v in result)
   self.logical_denoisers+=2;self.physical_pairs+=1
   cond=tuple(v[:1] for v in result);uncond=tuple(v[1:2] for v in result)
   self.pending=((id(hidden_states),id(timestep),id(kw.get('action_latents'))),uncond)
   return cond
  self.paired=paired;self.set_mode('baseline')
 @property
 def calls(self):return self.base.calls+2*self.gate_calls
 def set_mode(self,mode):
  assert mode in ('baseline','candidate');self.mode=mode
  self.base.set_mode(mode)
  # Other module forwards are reset by the inherited mode switch.
  for m,old,new in self.extra:
   if isinstance(m,DomainAwareLinear) or (isinstance(m,LinearBase) and id(m) not in self.gen_ids):
    m.forward=old
  if mode=='candidate':
   for m,old,new in self.extra:m.forward=new
   self.runner.forward=self.paired
  else:self.runner.forward=self.old_forward
 def full(self,pixels,request,vae_runner,engine):
  self.request=request;self.pending=None
  try:
   result=self.base.full(pixels,request,vae_runner,engine)
   assert self.pending is None
   return result
  finally:self.request=None;self.pending=None
 def close(self):
  self.runner.forward=self.old_forward
  for m,old,new in self.extra:m.forward=old
  self.base.close()
  for plan,idx,ws in self.plans.values():self.lib.lt_free(plan)
def install(transformer,vae,engine):return Control(transformer,vae,engine)
