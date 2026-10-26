"""Exact-gated cuBLASLt GEN dispatch over the immutable accepted Cosmos3 route."""
from pathlib import Path
import ctypes,functools,importlib.util,json,os,subprocess
import torch
def load_frozen():
 task=Path(os.environ['COSMOS_TASK_ROOT'])
 spec=importlib.util.spec_from_file_location('cosmos_round2_frozen_route',task/'baseline/accepted/solution/candidate-v11.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
@functools.cache
def library():
 task=Path(os.environ['COSMOS_TASK_ROOT']);so=task/'cache/cublaslt_views_v6.so'
 if not so.is_file():
  so.parent.mkdir(parents=True,exist_ok=True)
  subprocess.run(['/usr/bin/g++','-O3','-shared','-fPIC',str(task/'solution/cublaslt_views_v6.cc'),'-I/usr/local/cuda-13.0/include','-L/usr/local/cuda-13.0/lib64','-Wl,-rpath,/usr/local/cuda-13.0/lib64','-lcublasLt','-lcudart','-o',str(so)],check=True)
 lib=ctypes.CDLL(str(so));P=ctypes.c_void_p;I=ctypes.c_int;S=ctypes.c_size_t
 for n,args,ret in [('lt_make_view',[I,I,I,I,I,S,I],P),('lt_configure',[P,ctypes.POINTER(I),S],I),('lt_run',[P,I,P,P,P,P,S,P],I),('lt_free',[P],None)]:
  f=getattr(lib,n);f.argtypes=args;f.restype=ret
 return lib
class Control:
 def __init__(self,transformer,vae,engine,selection='cublaslt-selected-view-v6.json'):
  self.base=load_frozen().install(transformer,vae,engine)
  self.calls=0;self.plans={};self.workspaces={};self.bindings=[];self.packed_bytes=0;self.lib=library()
  self.selection=json.loads((Path(os.environ['COSMOS_TASK_ROOT'])/'solution'/selection).read_text())
  self.plan_spec=self.selection['configurations']
  # Reuse the frozen route's 3.375 GiB down-layout allocation; no duplicate packing.
  inherited={id(m):(packed,packed.__defaults__[1]) for m,old,direct,packed in self.base.base.bindings}
  for name,m in transformer.named_modules():
   if id(m) not in inherited:continue
   frozen,b=inherited[id(m)]
   category=name.split('.',2)[2].replace('.','_')
   selected=self.plan_spec.get(category)
   if selected is None:continue
   wanted_row=bool(selected['b_row'])
   if bool(b.stride(-1)==1)!=wanted_row:
    original=m.weight.t()
    b=original.contiguous() if wanted_row else original
    if b is not original:self.packed_bytes+=b.numel()*b.element_size()
   swapped=int(selected['swapped'])
   def fast(x,_frozen=frozen,_b=b,_category=category,_attrs=selected['attrs'],_swapped=swapped):
    if x.dtype!=torch.bfloat16 or not x.is_cuda or x.shape[-1]!=_b.shape[0]:return _frozen(x)
    aa=x.reshape(-1,x.shape[-1])
    if aa.shape[0]!=3542 or aa.stride(-1)!=1 or aa.stride(0)!=aa.shape[1]:return _frozen(x)
    stream=torch.cuda.current_stream(aa.device).cuda_stream
    key=(tuple(aa.shape),tuple(_b.shape),tuple(_b.stride()),aa.device.index,stream,_category)
    if key not in self.plans:
     wskey=(aa.device.index,stream)
     if wskey not in self.workspaces:self.workspaces[wskey]=torch.empty(64*1024*1024,device=aa.device,dtype=torch.uint8)
     ws=self.workspaces[wskey]
     plan=self.lib.lt_make_view(aa.shape[0],_b.shape[1],aa.shape[1],int(_b.stride(-1)==1),_swapped,ws.numel(),1)
     values=(ctypes.c_int*9)(*[_attrs[str(i)] for i in range(9)])
     idx=self.lib.lt_configure(plan,values,ws.numel())
     if idx<0:self.lib.lt_free(plan);raise RuntimeError(('Rejected cuBLASLt configuration',_category,idx))
     self.plans[key]=(plan,idx,ws)
    plan,idx,ws=self.plans[key]
    out=torch.empty((aa.shape[0],_b.shape[1]),device=aa.device,dtype=aa.dtype)
    ap,bp=(_b,aa) if _swapped else (aa,_b)
    status=self.lib.lt_run(plan,idx,ap.data_ptr(),bp.data_ptr(),out.data_ptr(),ws.data_ptr(),ws.numel(),stream)
    if status!=0:raise RuntimeError(('cuBLASLt dispatch failed',_category,status))
    self.calls+=1
    return out.reshape(*x.shape[:-1],_b.shape[1]),None
   self.bindings.append((m,frozen,fast))
  assert len(self.bindings)==144,len(self.bindings)
  self.set_mode('baseline')
 def set_mode(self,mode):
  assert mode in ('baseline','candidate')
  self.base.set_mode('combined_packed_exact');self.mode=mode
  if mode=='candidate':
   for m,frozen,fast in self.bindings:m.forward=fast
 def full(self,*args,**kwargs):return self.base.full(*args,**kwargs)
 def close(self):
  self.base.close()
  for p,i,w in self.plans.values():self.lib.lt_free(p)
  self.plans.clear();self.workspaces.clear()
