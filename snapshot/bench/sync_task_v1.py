from pathlib import Path
import argparse,io,tarfile,subprocess,shlex,json
p=argparse.ArgumentParser();p.add_argument('--remote-root',required=True);p.add_argument('--local-root',required=True);p.add_argument('paths',nargs='+');a=p.parse_args()
root=Path(a.local_root).resolve();buf=io.BytesIO();count=0
with tarfile.open(fileobj=buf,mode='w:gz') as tf:
 for rel in a.paths:
  src=(root/rel).resolve();assert src.is_relative_to(root)
  for f in sorted(src.rglob('*')) if src.is_dir() else [src]:
   if f.is_file() and not f.is_symlink() and not any(s in f.relative_to(root).parts for s in ['.git','__pycache__','.pytest_cache']):
    tf.add(f,arcname=str(f.relative_to(root)),recursive=False);count+=1
remote="""from pathlib import Path
import sys,io,tarfile,json,hashlib
root=Path(sys.argv[1]);allowed=Path('/home/tomorin/rjc').resolve()
assert not root.is_symlink() and root.resolve().is_relative_to(allowed) and root.resolve()!=allowed
root.mkdir(parents=True,exist_ok=True);root=root.resolve()
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()),mode='r:gz') as tf:
 members=tf.getmembers()
 for m in members:
  dst=(root/m.name).resolve();assert m.isfile() and dst.is_relative_to(root)
  data=tf.extractfile(m).read()
  if dst.exists():assert dst.read_bytes()==data,'Refuse different content: '+m.name
  else:dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
  if dst.suffix=='.sh':dst.chmod(0o755)
print(json.dumps({'root':str(root),'verified_files':len(members)}))
"""
ssh=['docker','exec','-i','thor-bridge','ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=45','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=4','-o','ControlMaster=auto','-o','ControlPersist=600','-o','ControlPath=/tmp/cosmos3-round2-20261021-%C','tomorin@172.30.3.112']
r=subprocess.run([*ssh,shlex.join(['python3','-B','-c',remote,a.remote_root])],input=buf.getvalue(),timeout=240)
print(json.dumps({'sent_files':count,'compressed_bytes':len(buf.getvalue()),'returncode':r.returncode}))
raise SystemExit(r.returncode)
