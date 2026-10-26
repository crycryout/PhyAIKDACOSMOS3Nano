"""Run a task harness and retain hashes of this process's mapped binaries."""
from pathlib import Path
import hashlib,json,os,runpy,sys
task=Path(__file__).resolve().parents[1]
name=sys.argv.pop(1)
assert Path(name).name==name and name.endswith('.py')
harness=(task/'bench'/name).resolve()
assert harness.parent==(task/'bench').resolve() and harness.is_file()
sys.argv[0]=str(harness)
out=Path(sys.argv[sys.argv.index('--out')+1]).resolve()
assert out.is_relative_to(task)
def snapshot():
 paths=set()
 for line in Path('/proc/self/maps').read_text().splitlines():
  fields=line.split(None,5)
  if len(fields)==6 and fields[5].startswith('/') and '.so' in fields[5]:
   p=Path(fields[5].removesuffix(' (deleted)'))
   if p.is_file():paths.add(p)
 rows=[]
 for p in sorted(paths):
  try:
   h=hashlib.sha256()
   with p.open('rb') as f:
    for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
   rows.append({'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest(),'provenance':'mapped in /proc/self/maps'})
  except OSError as error:rows.append({'path':str(p),'error':str(error)})
 generated=[]
 for folder in (task/'cache/triton',task/'cache/torchinductor',task/'cache/phyai_kernel'):
  if not folder.is_dir():continue
  for p in sorted(folder.rglob('*')):
   if p.is_file() and p.suffix in ('.so','.cubin','.fatbin','.ptx'):
    generated.append({'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'provenance':'task cache inventory; individual execution unproven'})
 return {'pid':os.getpid(),'harness':str(harness),'mapped_binaries':rows,'generated_cache_inventory':generated}
release_context=None
try:
 from early_cuda_context_v1 import retain
 release_context=retain(task,out)
 runpy.run_path(str(harness),run_name='__main__')
finally:
 out.mkdir(parents=True,exist_ok=True)
 manifest=snapshot()
 (out/'runtime-binary-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps({'binary_manifest':str(out/'runtime-binary-hashes.json'),'mapped_binary_count':len(manifest['mapped_binaries'])}),flush=True)

 # Retain the explicit primary-context reference until normal process exit.
 # Torch/CUPTI globals can outlive runpy's returned namespace; the CUDA driver
 # reclaims process-owned context references after Python library teardown.
 (out/'cuda-context-lifetime.json').write_text(json.dumps(dict(context_retained_until_process_exit=release_context is not None,explicit_release_before_python_teardown=False,normal_exit_and_errors_preserved=True))+'\n')
