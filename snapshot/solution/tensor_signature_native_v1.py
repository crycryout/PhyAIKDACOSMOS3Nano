"""Task-local CPU metadata extension; no CUDA compilation or kernel launch."""
from pathlib import Path
import hashlib,importlib.util,json,os,shlex,subprocess,sys,sysconfig,torch

NAME='cosmos_tensor_signature_v1'
def reference_encode(signatures):
    """Independent Python serialization of the complete v4 tensor signatures."""
    import struct
    result=bytearray(b'CTSIG1\0\0')
    def word(value):result.extend(struct.pack('<Q',int(value)&((1<<64)-1)))
    word(len(signatures))
    for identity,pointer,version,shape,stride,dtype,device,offset in signatures:
        for value in (identity,pointer,version,id(dtype)):word(value)
        name=device.type.encode('ascii');word(len(name));result.extend(name)
        word(-1 if device.index is None else device.index);word(offset);word(len(shape))
        for value in (*shape,*stride):word(value)
    return bytes(result)

def load():
    source=Path(__file__).with_suffix('.cc')
    task=source.parents[1]
    info=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),torch=torch.__version__,
              abi=bool(torch._C._GLIBCXX_USE_CXX11_ABI),python=sys.version,platform=sysconfig.get_platform())
    digest=hashlib.sha256(json.dumps(info,sort_keys=True).encode()).hexdigest()[:20]
    cache=task/'cache/native-tensor-signatures-v1'/digest
    cache.mkdir(parents=True,exist_ok=True)
    binary=cache/(NAME+sysconfig.get_config_var('EXT_SUFFIX'))
    metadata=cache/'build.json'
    if not binary.is_file():
        torch_root=Path(torch.__file__).parent
        compiler=shlex.split(os.environ.get('CXX','c++'))
        cmd=[*compiler,'-O3','-std=c++17','-shared','-fPIC',
             '-D_GLIBCXX_USE_CXX11_ABI='+str(int(info['abi'])),
             '-I'+str(torch_root/'include'),'-I'+str(torch_root/'include/torch/csrc/api/include'),
             '-I'+sysconfig.get_paths()['include'],str(source),'-o',str(binary),
             '-L'+str(torch_root/'lib'),'-Wl,-rpath,'+str(torch_root/'lib'),
             '-ltorch_python','-ltorch_cpu','-lc10']
        result=subprocess.run(cmd,capture_output=True,text=True)
        (cache/'compiler.stdout').write_text(result.stdout)
        (cache/'compiler.stderr').write_text(result.stderr)
        if result.returncode:raise RuntimeError('CPU metadata build failed: '+result.stderr[-4000:])
        info.update(command=cmd,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),cuda_compiled=False)
        with metadata.open('x') as f:json.dump(info,f,indent=2)
    stored=json.loads(metadata.read_text())
    if stored['source_sha256']!=info['source_sha256'] or stored['binary_sha256']!=hashlib.sha256(binary.read_bytes()).hexdigest():
        raise RuntimeError('Native metadata build hash mismatch')
    if NAME in sys.modules:
        loaded=sys.modules[NAME]
        if Path(loaded.__file__).resolve()!=binary.resolve():raise RuntimeError('Different metadata extension already loaded')
        return loaded
    spec=importlib.util.spec_from_file_location(NAME,binary)
    loaded=importlib.util.module_from_spec(spec);spec.loader.exec_module(loaded);sys.modules[NAME]=loaded
    return loaded
