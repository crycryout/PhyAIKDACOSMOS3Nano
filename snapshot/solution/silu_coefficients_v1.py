"""Exact finite-domain SiLU coefficients; no model-output memoization."""
from pathlib import Path
import ctypes,functools,hashlib,os,subprocess,torch
@functools.cache
def library():
 task=Path(os.environ['COSMOS_TASK_ROOT']);source=task/'solution/silu_coefficients_v1.cu';so=task/'cache/silu_coefficients_v1.so'
 if not so.is_file():
  so.parent.mkdir(parents=True,exist_ok=True)
  subprocess.run(['/usr/local/cuda-13.0/bin/nvcc','-O3','--use_fast_math','-lineinfo','-shared','-Xcompiler','-fPIC','-arch=sm_110a',str(source),'-o',str(so)],check=True)
 lib=ctypes.CDLL(str(so));P=ctypes.c_void_p;I=ctypes.c_int
 lib.silu_table_build.argtypes=[P,P];lib.silu_table_build.restype=I
 lib.silu_table_apply.argtypes=[P,P,P,I,I,I,I,P];lib.silu_table_apply.restype=I
 return lib
class Silu:
 def __init__(self,device,threads=256,use_table=True):
  self.lib=library();self.threads=threads;self.use_table=use_table
  with torch.cuda.device(device):
   self.table=torch.empty(65536,device=device,dtype=torch.float32)
   stream=torch.cuda.current_stream(device)
   status=self.lib.silu_table_build(self.table.data_ptr(),stream.cuda_stream);assert status==0,status
   self.ready=torch.cuda.Event();self.ready.record(stream)
 def __call__(self,x,out=None):
  assert x.is_cuda and x.device==self.table.device and x.dtype==torch.bfloat16 and x.is_contiguous() and x.shape[-1]%16==0
  n=x.shape[-1]//2;rows=x.numel()//(2*n)
  if out is None:out=torch.empty((*x.shape[:-1],n),device=x.device,dtype=x.dtype)
  assert out.dtype==x.dtype and out.is_contiguous() and out.shape==(*x.shape[:-1],n) and out.device==x.device
  stream=torch.cuda.current_stream(x.device);stream.wait_event(self.ready)
  status=self.lib.silu_table_apply(x.data_ptr(),out.data_ptr(),self.table.data_ptr(),rows,n,self.threads,int(self.use_table),stream.cuda_stream);assert status==0,status
  return out
