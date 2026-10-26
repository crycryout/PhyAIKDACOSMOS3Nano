"""Read bounded Thor task status or fetch task evidence with member path checks."""
from pathlib import Path
import argparse,io,json,subprocess,tarfile,shlex
p=argparse.ArgumentParser(__doc__)
p.add_argument("--remote-root",required=True)
p.add_argument("--local-root",required=True)
p.add_argument("--status",action="store_true")
p.add_argument("paths",nargs="+")
a=p.parse_args()
code=r"""
from pathlib import Path
import io,json,sys,tarfile
root=Path(sys.argv[1]);assert not root.is_symlink()
root=root.resolve();assert root.is_relative_to(Path('/home/tomorin/rjc').resolve())
paths=json.loads(sys.argv[2]);status=sys.argv[3]=='1'
if status:
 for rel in paths:
  f=(root/rel).resolve();assert f.is_relative_to(root)
  if not f.is_file():print(json.dumps(dict(path=rel,pending=True)));continue
  if f.name=='validation.json':
   d=json.loads(f.read_text());print(json.dumps(dict(path=rel,complete=d['complete'],gate=d['exact_gate_passed'],cases=[{k:r[k] for k in ['case','byte_equal','ready_wall_ms','phase_counts'] if k in r} for r in d['cases']])))
  elif f.name=='run.json':
   d=json.loads(f.read_text());print(json.dumps(dict(path=rel,returncode=d.get('returncode'),interference=d.get('interference_observed'),before=d.get('before',{}).get('gpu_processes'))))
  else:print(json.dumps(dict(path=rel,tail=f.read_text(errors='replace')[-8000:])))
else:
 buf=io.BytesIO()
 with tarfile.open(fileobj=buf,mode='w:gz') as t:
  for rel in paths:
   src=(root/rel).resolve();assert src.is_relative_to(root) and src.exists()
   for f in sorted(src.rglob('*')) if src.is_dir() else [src]:
    if f.is_file() and not f.is_symlink() and 'scratch' not in f.relative_to(root).parts:
     t.add(f,arcname=str(f.relative_to(root)),recursive=False)
 sys.stdout.buffer.write(buf.getvalue())
"""
ssh=["docker","exec","-i","thor-bridge","ssh","-T","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=15","-o","ServerAliveInterval=15","-o","ServerAliveCountMax=4","tomorin@172.30.3.112"]
r=subprocess.run([*ssh,shlex.join(["python3","-B","-c",code,a.remote_root,json.dumps(a.paths),"1" if a.status else "0"])],capture_output=True,timeout=180)
if r.returncode:
 print(r.stderr.decode(errors="replace"));raise SystemExit(r.returncode)
if a.status:
 print(r.stdout.decode())
else:
 root=Path(a.local_root).resolve()
 count=0
 with tarfile.open(fileobj=io.BytesIO(r.stdout),mode="r:gz") as t:
  for m in t.getmembers():
   assert m.isfile()
   dst=(root/m.name).resolve();assert dst.is_relative_to(root)
   content=t.extractfile(m).read()
   if dst.exists():assert dst.read_bytes()==content,"Existing evidence differs: "+str(dst)
   else:dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(content)
   count+=1
 print(json.dumps(dict(fetched=count,compressed_bytes=len(r.stdout),root=str(root))))
