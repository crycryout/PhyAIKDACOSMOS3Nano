"""Retain this benchmark process's primary CUDA context before heavy imports.

No GPU kernels, model input, or timed region is changed. Fixed PhyAI CUDA
defaults apply before context creation; every foreign-process gate remains.
"""
from pathlib import Path
import ctypes,datetime,json,os,subprocess,time
def retain(task,out):
    task=Path(task).resolve();out=Path(out).resolve()
    assert out.is_relative_to(task) and task.is_relative_to(Path('/home/tomorin/rjc').resolve())
    out.mkdir(parents=True,exist_ok=True)
    row={'pid':os.getpid(),'outside_e2e':True,'model_requests':0,'gpu_kernels_launched':0,
         'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    def write():
        (out/'early-cuda-context.json').write_text(json.dumps(row,indent=2)+'\n')
    def processes():
        r=subprocess.run(['/usr/sbin/nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader'],capture_output=True,text=True,check=True)
        return [line for line in r.stdout.splitlines() if line.strip() and int(line.split(',')[0])!=os.getpid()]
    before=processes();row['foreign_before']=before;write()
    if before:
        row['admission_deferred']=True;write();raise SystemExit(75)
    assert os.environ.get('CUDA_VISIBLE_DEVICES') in (None,'','0')
    defaults={'CUDA_DEVICE_MAX_CONNECTIONS':'8','CUDA_MODULE_LOADING':'LAZY'}
    row['initial_environment']={k:os.environ.get(k) for k in defaults}
    for key,value in defaults.items():
        assert os.environ.get(key) in (None,value),(key,'unexpected frozen CUDA setting')
        os.environ.setdefault(key,value)
    lib=ctypes.CDLL('libcuda.so.1')
    def check(name,*args):
        result=getattr(lib,name)(*args)
        if result:raise RuntimeError(name+' failed with CUDA driver result '+str(result))
    device=ctypes.c_int();count=ctypes.c_int();ctx=ctypes.c_void_p()
    check('cuInit',0);check('cuDeviceGetCount',ctypes.byref(count))
    assert count.value==1,'Fixed Thor task requires one visible physical GPU'
    check('cuDeviceGet',ctypes.byref(device),0)
    check('cuDevicePrimaryCtxRetain',ctypes.byref(ctx),device)
    released=False
    def release():
        nonlocal released
        if not released:
            check('cuDevicePrimaryCtxRelease_v2',device);released=True
    try:
        check('cuCtxSetCurrent',ctx)
        row['context_ready_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        row['effective_cuda_environment']={k:os.environ[k] for k in defaults}
        row['foreign_after']=processes();row['context_retained']=True;write()
        if row['foreign_after']:
            row['admission_deferred']=True;write();release();raise SystemExit(75)
        print('EARLY_CUDA_CONTEXT '+json.dumps(row),flush=True)
        return release
    except BaseException:
        release();raise
