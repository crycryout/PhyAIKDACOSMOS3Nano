"""Exact pure-operator CSE within one CFG pair; all real forwards still run.

v2 adds physical RMS/SiLU reuse to v1's source-derived input proof. It explicitly
does not claim to execute every redundant nonlinear CUDA kernel. No layer,
denoiser, request output, or value from a preceding denoise step is memoized.
"""
from pathlib import Path
import collections,importlib.util,torch
_spec=importlib.util.spec_from_file_location('cosmos_r3_pure_parent',Path(__file__).with_name('candidate-round3-v1.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
def tensors(value):
 if isinstance(value,torch.Tensor):return [value]
 if isinstance(value,(tuple,list)):return [t for v in value for t in tensors(v)]
 if isinstance(value,dict):return [t for _,v in sorted(value.items()) for t in tensors(v)]
 return []
def metadata(value):
 if isinstance(value,torch.Tensor):return ('tensor',tuple(value.shape),tuple(value.stride()),value.dtype,value.device)
 if isinstance(value,(tuple,list)):return (type(value).__name__,tuple(metadata(v) for v in value))
 if isinstance(value,dict):return ('dict',tuple((k,metadata(v)) for k,v in sorted(value.items())))
 if value is None or isinstance(value,(bool,int,float,str)):return value
 raise parent.NotProven('unsupported_pure_operator_argument')
def version(t):return parent.parent.r2.version(t)
def versions(values):return tuple(version(t) for t in values)
def byte_equal(a,b):
 if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and metadata(a)==metadata(b) and torch.equal(a.contiguous().view(torch.uint8),b.contiguous().view(torch.uint8))
 if isinstance(a,(tuple,list)):return type(a)==type(b) and len(a)==len(b) and all(byte_equal(x,y) for x,y in zip(a,b))
 return a==b
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.pure_bindings=[];self.pure_namespace=None;self.pure_entries={};self.pure_phase=None;self.pure_counts=collections.Counter()
  self.pure_bytes=0;self.pure_peak=0;self.pure_cap=24*1024**3;self.audit_pure=False;self.pure_counters=collections.Counter()
  super().__init__(transformer,vae,engine)
  for index,layer in enumerate(transformer.gen_layers):
   for kind,mod in [('input_rms',layer.input_layernorm),('post_rms',layer.post_attention_layernorm),('q_rms',layer.cross_attention.norm_q),('k_rms',layer.cross_attention.norm_k)]:
    old=mod.forward
    def forward(*args,_key=(kind,index),_old=old,**kwargs):
     # In-place RMS residual calls are outside this supported pure ABI.
     if len(args)>1 and args[1] is not None or kwargs.get('residual') is not None:return _old(*args,**kwargs)
     return self.pure_call(_key,_old,args,kwargs)
    self.pure_bindings.append((mod,'forward',old,forward))
   mod=layer.mlp;old=mod._act_and_mul
   def activate(*args,_key=('silu',index),_old=old,**kwargs):return self.pure_call(_key,_old,args,kwargs)
   self.pure_bindings.append((mod,'_act_and_mul',old,activate))
  namespace=transformer.gen_layers[0].forward.__globals__
  assert 'rounded_add_rmsnorm' in namespace
  assert all(layer.forward.__globals__ is namespace for layer in transformer.gen_layers)
  self.pure_namespace=namespace;self.original_rounded=namespace['rounded_add_rmsnorm']
  def rounded(*args,**kwargs):
   self.enter_pure_phase()
   index=self.pure_counts['rounded_rms'];self.pure_counts['rounded_rms']+=1
   return self.pure_call(('rounded_rms',index),self.original_rounded,args,kwargs)
  self.pure_rounded=rounded;self.set_mode('baseline')
 def signature(self,*args,**kwargs):
  from phyai.kernel.bootstrap import get_kernel_selector
  selector=get_kernel_selector()
  return super().signature(*args,**kwargs)+(id(selector),selector.epoch,torch.are_deterministic_algorithms_enabled())
 def clear_pure(self):
  self.pure_entries.clear();self.pure_counts.clear();self.pure_phase=None;self.pure_bytes=0
 def enter_pure_phase(self):
  phase=self.frozen.phase
  if phase!=self.pure_phase:
   if phase=='cond':self.clear_pure()
   self.pure_counts.clear();self.pure_phase=phase
  return phase
 def pure_call(self,key,fn,args,kwargs):
  phase=self.enter_pure_phase()
  if self.mode!='candidate' or phase not in ('cond','uncond'):return fn(*args,**kwargs)
  kind=key[0];self.pure_counters[(kind,'logical')]+=1
  current=tensors((args,kwargs))
  try:
   meta=metadata((args,kwargs))
   assert current and all(t.is_cuda and version(t) is not None for t in current)
  except (parent.NotProven,AssertionError):
   self.pure_counters[(kind,'physical')]+=1;return fn(*args,**kwargs)
  stream=torch.cuda.current_stream(current[0].device).cuda_stream
  if phase=='uncond':
   entry=self.pure_entries.pop(key,None)
   if entry is not None:
    saved,iv,result,ov,old_meta,output_meta,old_stream,nbytes=entry;self.pure_bytes-=nbytes
    output=tensors(result)
    valid=(self.proof_active and meta==old_meta and versions(saved)==iv and versions(output)==ov and metadata(result)==output_meta and stream==old_stream)
    if valid:
     if self.audit_pure:
      actual=fn(*args,**kwargs);self.pure_counters[(kind,'audit_recomputations')]+=1
      assert byte_equal(actual,result),('Pure operator CSE byte audit failed',key)
     self.pure_counters[(kind,'reused')]+=1;return result
   self.pure_counters[(kind,'fallback')]+=1;self.pure_counters[(kind,'physical')]+=1
   return fn(*args,**kwargs)
  input_versions=versions(current)
  result=fn(*args,**kwargs);self.pure_counters[(kind,'physical')]+=1;output=tensors(result)
  if not output or versions(current)!=input_versions or any(version(t) is None for t in output):return result
  if any(x.data_ptr()==y.data_ptr() for x in current for y in output):return result
  nbytes=sum(t.numel()*t.element_size() for t in (*current,*output))
  if self.pure_bytes+nbytes<=self.pure_cap:
   self.pure_entries[key]=(current,input_versions,result,versions(output),meta,metadata(result),stream,nbytes)
   self.pure_bytes+=nbytes;self.pure_peak=max(self.pure_peak,self.pure_bytes)
  return result
 def set_mode(self,mode):
  self.clear_pure();super().set_mode(mode)
  for mod,name,old,new in self.pure_bindings:setattr(mod,name,new if mode=='candidate' else old)
  if self.pure_namespace is not None:self.pure_namespace['rounded_add_rmsnorm']=self.pure_rounded if mode=='candidate' else self.original_rounded
 def full(self,*args,**kwargs):
  self.clear_pure();self.pure_peak=0;before=self.pure_counters.copy()
  try:return super().full(*args,**kwargs)
  finally:
   stats=self.pure_counters-before
   # Counters are total logical evaluations; audit recomputations are separate.
   self.last_request_stats['pure_operator_reuse']=dict(by_kind={kind:{field:stats[(kind,field)] for field in ('logical','physical','reused','fallback','audit_recomputations')} for kind in ('rounded_rms','input_rms','post_rms','q_rms','k_rms','silu')},peak_accounted_reference_bytes=self.pure_peak,cap_bytes=self.pure_cap,remaining_entries_before_request_cleanup=len(self.pure_entries),audit=self.audit_pure,physical_nonlinear_kernels_may_be_reused=True,lifetime='one CFG pair; no layer, branch, step or request output cache')
   self.last_request_stats['input_proof']['all_nonlinear_operations_executed']=False
   self.clear_pure();self.last_request_stats['pure_operator_reuse']['remaining_entries']=len(self.pure_entries)
 def close(self):
  self.clear_pure()
  for mod,name,old,new in self.pure_bindings:setattr(mod,name,old)
  if self.pure_namespace is not None:self.pure_namespace['rounded_add_rmsnorm']=self.original_rounded
  super().close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
