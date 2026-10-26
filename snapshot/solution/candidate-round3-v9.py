"""v9: v8 with exact, batched CPU proof signatures.

The native extension reads metadata only. All guarded fields remain present;
a changed route runs the complete parent signature, and unsupported tensors
decline the proof. No device data is cached between CFG pairs or requests.
"""
from pathlib import Path
import importlib.util,torch
_spec=importlib.util.spec_from_file_location('cosmos_r3_v9_parent',Path(__file__).with_name('candidate-round3-v8.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
_native_spec=importlib.util.spec_from_file_location('cosmos_r3_native_v2_loader',Path(__file__).with_name('tensor_signature_native_v2.py'))
native_loader=importlib.util.module_from_spec(_native_spec);_native_spec.loader.exec_module(native_loader)
v4=parent.parent.parent
proof=v4.proof
function_id=proof.function_id
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.native_signature=None;self.native_route_records=None;self.native_route=None
  self.native_fast_calls=0;self.native_refresh_calls=0;self.native_audits=0
  super().__init__(transformer,vae,engine)
  self.native_signature=native_loader.load()
  self.native_weight_names=tuple(name for name,value in (*self.parameters,*self.buffers))
 def pack_parent(self,result,args,kwargs):
  tensors,constants,weights=result[:3]
  signatures=[tensors[0],tensors[1]]
  kwargs_shape=[]
  for key,value in sorted(kwargs.items()):
   entry=next(v for k,v in tensors[2:] if k==key)
   if isinstance(value,torch.Tensor):
    kwargs_shape.append((key,'tensor'));signatures.append(entry)
   else:kwargs_shape.append((key,'value',entry))
  signatures.extend(constants[3]);signatures.extend(constants[4])
  signatures.extend(value for name,value in weights)
  meta=(*constants[:3],len(constants[3]),len(constants[4]),constants[5])
  return (native_loader.reference_encode(signatures),tuple(kwargs_shape),meta,
          tuple(name for name,value in weights),*result[3:])
 def refresh_records(self,result):
  self.native_route=result[3]
  self.native_route_records=tuple(
    (mod,cls,mod.__dict__,v4.dict_get_version(mod.__dict__),
     getattr(cls,'forward',None),getattr(cls,'_act_and_mul',None),registries)
    for name,mod,cls,registries in self.registry_snapshot)
 def signature(self,args,kwargs):
  if self.native_signature is None or v4.dict_get_version is None:
   return super().signature(args,kwargs)
  if len(args)!=3:raise proof.NotProven('unsupported_transformer_call')
  hidden,timestep,condition=args
  from dynamic_contract_v2 import require_condition
  require_condition(args,kwargs,self.transformer,proof.NotProven)
  import torch.nn.modules.module as module_hooks
  if module_hooks._global_forward_hooks or module_hooks._global_forward_pre_hooks:raise proof.NotProven('global_hooks')
  if self.native_route_records is None or not self.native_signature.scan_routes(self.native_route_records):
   expected=super().signature(args,kwargs)
   self.refresh_records(expected);self.native_refresh_calls+=1
   return self.pack_parent(expected,args,kwargs)
  values=[hidden,timestep];kwargs_shape=[]
  for key,value in sorted(kwargs.items()):
   if isinstance(value,torch.Tensor):
    values.append(value);kwargs_shape.append((key,'tensor'))
   else:kwargs_shape.append((key,'value',value))
  cached=tuple(t for kv in condition.cached_kv for t in kv)
  frequencies=tuple(condition.freqs_gen)
  values.extend(cached);values.extend(frequencies)
  values.extend(value for name,value in (*self.parameters,*self.buffers))
  try:blob=self.native_signature.encode(values)
  except RuntimeError as error:raise proof.NotProven('unsupported_native_tensor_metadata: '+str(error)) from error
  self.proof_refs.extend(values)
  meta=(condition.video_shape,condition.action_len,condition.sound_len,
        len(cached),len(frequencies),function_id(condition.attention_preparation))
  from phyai.kernel.bootstrap import get_kernel_selector
  selector=get_kernel_selector();provider=self.prepare_provider
  result=(blob,tuple(kwargs_shape),meta,self.native_weight_names,self.native_route,
    torch.cuda.current_stream(hidden.device).cuda_stream,
    torch.is_autocast_enabled('cuda'),torch.get_float32_matmul_precision(),
    id(selector),selector.epoch,torch.are_deterministic_algorithms_enabled(),
    provider.enabled,id(provider._compiled),provider._recompile_limit_hit,function_id(self.original_preparation),
    function_id(provider.prepare),function_id(provider.forward),
    function_id(self.helper_namespace['prepare_cosmos3_attention']),
    function_id(self.attention_namespace['extension']),id(self.pv144_extension))
  self.native_fast_calls+=1
  if self.audit_signature:
   expected=super().signature(args,kwargs)
   assert result==self.pack_parent(expected,args,kwargs),'Batched proof differs from complete parent proof'
   self.native_audits+=1
  return result
 def full(self,*args,**kwargs):
  before=(self.native_fast_calls,self.native_refresh_calls,self.native_audits)
  try:return super().full(*args,**kwargs)
  finally:
   self.last_request_stats['native_signature']=dict(
    fast_calls=self.native_fast_calls-before[0],
    refresh_calls=self.native_refresh_calls-before[1],
    audited_fast_calls=self.native_audits-before[2],
    tensors_checked_each_forward=True,route_guard_fields_preserved=True)
 def close(self):
  self.native_route_records=None;self.native_route=None
  super().close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
