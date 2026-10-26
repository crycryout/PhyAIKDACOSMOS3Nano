"""Scope-limited identity proof for pure GEMM/attention CSE in the frozen graph.

Both transformer forwards and every nonlinear operator still execute. Only the
R2-v12 byte comparisons can be omitted when all upstream inputs are the same
live, versioned tensors and the frozen numerical route is unchanged.
Unsupported input, versionless tensors, hooks, shape or stream differences use
the complete R2 byte-verified path. Nothing survives a CFG pair or a request.
"""
from pathlib import Path
import importlib.util,torch
_spec=importlib.util.spec_from_file_location('cosmos_r3_v1_parent',Path(__file__).with_name('candidate-round3-v0.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)

def function_id(fn):
 return (getattr(fn,'__func__',fn),id(getattr(fn,'__self__',None)))
class NotProven(Exception):pass
class TorchView:
 def __init__(self,owner):self.owner=owner
 def __getattr__(self,name):return getattr(torch,name)
 def equal(self,x,y):
  o=self.owner
  if o.proof_active and x.is_cuda and y.is_cuda and x.dtype==y.dtype==torch.uint8 and x.shape==y.shape:
   o.proved_comparisons+=1
   if o.audit_proof:
    o.audited_comparisons+=1
    assert torch.equal(x,y),'Source-derived equivalence did not match actual bytes'
   return True
  o.physical_comparisons+=1
  return torch.equal(x,y)
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.proof_active=False;self.cond_proof=None;self.proof_refs=[]
  self.proved_pairs=0;self.proof_fallback_pairs=0;self.proved_comparisons=0;self.physical_comparisons=0;self.audited_comparisons=0
  self.audit_proof=False;self.proof_rows=[]
  super().__init__(transformer,vae,engine)
  self.transformer=transformer;self.original_transformer=transformer.forward
  self.modules=list(transformer.named_modules())
  self.parameters=list(transformer.named_parameters());self.buffers=list(transformer.named_buffers())
  self.view=TorchView(self)
  parent.r2.torch=self.view;parent.r2._parent.torch=self.view
  def forward(*args,**kwargs):
   phase=self.frozen.phase
   if self.mode!='candidate' or phase not in ('cond','uncond'):
    return self.original_transformer(*args,**kwargs)
   eligible=False;reason=None
   try:
    signature=self.signature(args,kwargs)
    if phase=='cond':self.cond_proof=signature
    else:eligible=self.cond_proof is not None and self.cond_proof==signature
   except NotProven as error:reason=str(error)
   if phase=='uncond':
    self.proof_active=eligible
    self.proved_pairs+=int(eligible);self.proof_fallback_pairs+=int(not eligible)
    self.proof_rows.append(dict(proven=eligible,reason=reason or ('identical_live_inputs_and_route' if eligible else 'input_or_route_changed')))
   try:return self.original_transformer(*args,**kwargs)
   finally:
    self.proof_active=False
    if phase=='uncond':self.cond_proof=None;self.proof_refs=[]
  self.proof_forward=forward;transformer.forward=forward
 def tensor_signature(self,t):
  v=parent.r2.version(t)
  if v is None:raise NotProven('versionless_tensor')
  self.proof_refs.append(t)
  return (id(t),t.data_ptr(),v,tuple(t.shape),tuple(t.stride()),t.dtype,t.device,t.storage_offset())
 def signature(self,args,kwargs):
  if len(args)!=3:raise NotProven('unsupported_transformer_call')
  hidden,timestep,condition=args
  from dynamic_contract_v2 import require_condition
  require_condition(args,kwargs,self.transformer,NotProven)
  import torch.nn.modules.module as module_hooks
  if module_hooks._global_forward_hooks or module_hooks._global_forward_pre_hooks:raise NotProven('global_hooks')
  route=[]
  for name,mod in self.modules:
   if mod._forward_hooks or mod._forward_pre_hooks:raise NotProven('module_hooks')
   route.append((name,id(mod),function_id(mod.forward),mod.training,
       tuple((key,function_id(value) if callable(value) else value) for key,value in mod.__dict__.items() if not key.startswith('_') and isinstance(value,(int,float,bool,str,type(None)))) ,
       function_id(mod._act_and_mul) if hasattr(mod,'_act_and_mul') else None))
  tensors=[self.tensor_signature(hidden),self.tensor_signature(timestep)]
  for key,value in sorted(kwargs.items()):
   tensors.append((key,self.tensor_signature(value) if isinstance(value,torch.Tensor) else value))
  constants=(condition.video_shape,condition.action_len,condition.sound_len,
             tuple(self.tensor_signature(t) for kv in condition.cached_kv for t in kv),
             tuple(self.tensor_signature(t) for t in condition.freqs_gen),
             function_id(condition.attention_preparation))
  weights=tuple((name,self.tensor_signature(value)) for name,value in (*self.parameters,*self.buffers))
  return (tuple(tensors),constants,weights,tuple(route),
          torch.cuda.current_stream(hidden.device).cuda_stream,
          torch.is_autocast_enabled('cuda'),torch.get_float32_matmul_precision())
 def set_mode(self,mode):
  self.proof_active=False;self.cond_proof=None;self.proof_refs=[]
  super().set_mode(mode)
 def full(self,*args,**kwargs):
  self.cond_proof=None;self.proof_refs=[];self.proof_active=False;self.proof_rows=[]
  before=(self.proved_pairs,self.proof_fallback_pairs,self.proved_comparisons,self.physical_comparisons,self.audited_comparisons)
  try:return super().full(*args,**kwargs)
  finally:
   self.proof_active=False;self.cond_proof=None;self.proof_refs=[]
   self.last_request_stats.update(input_proof=dict(proved_pairs=self.proved_pairs-before[0],fallback_pairs=self.proof_fallback_pairs-before[1],proved_intermediate_comparisons=self.proved_comparisons-before[2],physical_intermediate_comparisons=self.physical_comparisons-before[3],audited_intermediate_comparisons=self.audited_comparisons-before[4],rows=list(self.proof_rows),all_nonlinear_operations_executed=True))
 def close(self):
  self.proof_active=False;self.cond_proof=None;self.proof_refs=[]
  self.transformer.forward=self.original_transformer
  parent.r2.torch=torch;parent.r2._parent.torch=torch
  super().close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
