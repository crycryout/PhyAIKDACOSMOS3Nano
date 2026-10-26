"""v4: cache unchanged route metadata while preserving the complete v3 proof.

CPython dictionary revisions guard cached immutable signature fragments.
Every tensor identity/version and stream is still checked per forward.
Registry replacement or mutation declines the proof. Other Python runtimes
use the complete parent signature. Audit mode compares each constructed
signature directly against the uncached parent implementation.
"""
from pathlib import Path
import importlib.util,torch
try:
 from _testcapi import dict_get_version
except ImportError:
 dict_get_version=None
_spec=importlib.util.spec_from_file_location('cosmos_r3_route_parent',Path(__file__).with_name('candidate-round3-v3.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
proof=parent.parent.parent
function_id=proof.function_id
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.route_cache={};self.audit_signature=False;self.signature_audits=0
  super().__init__(transformer,vae,engine)
  self.registry_snapshot=[]
  if dict_get_version is not None:
   for name,mod in self.modules:
    entries=tuple((key,mod.__dict__[key],dict_get_version(mod.__dict__[key])) for key in ('_modules','_parameters','_buffers'))
    self.registry_snapshot.append((name,mod,type(mod),entries))
 def signature(self,args,kwargs):
  if dict_get_version is None:return super().signature(args,kwargs)
  if len(args)!=3:raise proof.NotProven('unsupported_transformer_call')
  hidden,timestep,condition=args
  from dynamic_contract_v2 import require_condition
  require_condition(args,kwargs,self.transformer,proof.NotProven)
  import torch.nn.modules.module as module_hooks
  if module_hooks._global_forward_hooks or module_hooks._global_forward_pre_hooks:raise proof.NotProven('global_hooks')
  route=[]
  for name,mod,cls,registries in self.registry_snapshot:
   if type(mod) is not cls:raise proof.NotProven('module_class_changed')
   if mod._forward_hooks or mod._forward_pre_hooks:raise proof.NotProven('module_hooks')
   for key,registry,revision in registries:
    if mod.__dict__.get(key) is not registry or dict_get_version(registry)!=revision:
     raise proof.NotProven('module_registry_changed')
   key=(dict_get_version(mod.__dict__),getattr(cls,'forward',None),getattr(cls,'_act_and_mul',None))
   saved=self.route_cache.get(name)
   if saved is not None and saved[0]==key:
    row=saved[1]
   else:
    row=(name,id(mod),function_id(mod.forward),mod.training,
         tuple((field,function_id(value) if callable(value) else value) for field,value in mod.__dict__.items() if not field.startswith('_') and isinstance(value,(int,float,bool,str,type(None)))),
         function_id(mod._act_and_mul) if hasattr(mod,'_act_and_mul') else None)
    self.route_cache[name]=(key,row)
   route.append(row)
  tensors=[self.tensor_signature(hidden),self.tensor_signature(timestep)]
  for key,value in sorted(kwargs.items()):
   tensors.append((key,self.tensor_signature(value) if isinstance(value,torch.Tensor) else value))
  constants=(condition.video_shape,condition.action_len,condition.sound_len,
             tuple(self.tensor_signature(t) for kv in condition.cached_kv for t in kv),
             tuple(self.tensor_signature(t) for t in condition.freqs_gen),
             function_id(condition.attention_preparation))
  weights=tuple((name,self.tensor_signature(value)) for name,value in (*self.parameters,*self.buffers))
  from phyai.kernel.bootstrap import get_kernel_selector
  selector=get_kernel_selector();provider=self.prepare_provider
  result=(tuple(tensors),constants,weights,tuple(route),
          torch.cuda.current_stream(hidden.device).cuda_stream,
          torch.is_autocast_enabled('cuda'),torch.get_float32_matmul_precision(),
          id(selector),selector.epoch,torch.are_deterministic_algorithms_enabled(),
          provider.enabled,id(provider._compiled),provider._recompile_limit_hit,function_id(self.original_preparation))
  if self.audit_signature:
   expected=super().signature(args,kwargs)
   assert result==expected,'Cached route signature differs from complete parent signature'
   self.signature_audits+=1
  return result
 def full(self,*args,**kwargs):
  before=self.signature_audits
  try:return super().full(*args,**kwargs)
  finally:
   self.last_request_stats['route_signature_cache']=dict(available=dict_get_version is not None,entries=len(self.route_cache),audit=self.audit_signature,audited_signatures=self.signature_audits-before,registry_mutation_falls_back=True,tensor_checks_per_forward=True)
 def close(self):
  self.route_cache.clear()
  super().close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
