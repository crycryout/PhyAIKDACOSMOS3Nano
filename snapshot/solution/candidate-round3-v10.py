"""v10: upload the original UniPC sigma schedule once inside each request.

The original scheduler still creates both samplers, builds both schedules and
executes every solver operation. Only the location of the immutable FP32 sigma
table changes; dtype casts remain at their original use sites. No schedule,
latent or output is reused across requests.
"""
from pathlib import Path
import importlib.util,torch
_spec=importlib.util.spec_from_file_location('cosmos_r3_sigma_parent',Path(__file__).with_name('candidate-round3-v9.py'))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
class Control(parent.Control):
 def __init__(self,transformer,vae,engine):
  self.sampler_namespace=None;self.sigma_uploads=0;self.sigma_upload_bytes=0
  super().__init__(transformer,vae,engine)
  import phyai.models.cosmos3.scheduler_cosmos3_policy as policy
  self.sampler_namespace=policy.__dict__
  original=policy.UniPCMultistepSampler;self.original_sampler=original
  owner=self
  class DeviceSigmas(original):
   def set_timesteps(self,num_inference_steps,device=None):
    super().set_timesteps(num_inference_steps,device=device)
    if owner.mode=='candidate' and device is not None and torch.device(device).type=='cuda':
     assert self.sigmas.device.type=='cpu' and self.sigmas.dtype==torch.float32
     owner.sigma_uploads+=1;owner.sigma_upload_bytes+=self.sigmas.numel()*self.sigmas.element_size()
     self.sigmas=self.sigmas.to(device=device)
  self.device_sampler=DeviceSigmas
  self.set_mode('baseline')
 def set_mode(self,mode):
  super().set_mode(mode)
  if self.sampler_namespace is not None:
   self.sampler_namespace['UniPCMultistepSampler']=self.device_sampler if mode=='candidate' else self.original_sampler
 def signature(self,*args,**kwargs):
  result=super().signature(*args,**kwargs)
  if self.sampler_namespace is None:return result
  return result+(parent.function_id(self.sampler_namespace['UniPCMultistepSampler']),)
 def full(self,*args,**kwargs):
  before=(self.sigma_uploads,self.sigma_upload_bytes)
  try:return super().full(*args,**kwargs)
  finally:
   self.last_request_stats['sigma_schedule_upload']=dict(
    tables=self.sigma_uploads-before[0],bytes=self.sigma_upload_bytes-before[1],
    upload_inside_e2e=True,original_solver_methods=True,cross_request_reuse=False)
 def close(self):
  if self.sampler_namespace is not None:self.sampler_namespace['UniPCMultistepSampler']=self.original_sampler
  super().close()
def install(transformer,vae,engine):return Control(transformer,vae,engine)
