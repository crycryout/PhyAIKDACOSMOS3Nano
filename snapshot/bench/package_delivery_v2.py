
"""Publish completed V4 evidence; exclude all raw native traces/captures and verify staged bytes."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);p.add_argument("--repo",type=Path,required=True)
p.add_argument("--subdir",required=True);p.add_argument("--trace-id",required=True)
a=p.parse_args();t=a.task;repo=a.repo;dest=repo/a.subdir
assert dest.is_relative_to(repo/"examples") and not dest.exists(),dest
assert not subprocess.check_output(["git","status","--porcelain"],cwd=repo),"Require clean checkout"
main=[json.loads(l) for l in (t/"results/workflow-trace.jsonl").read_text().splitlines()]
assert main[-1]["event"]=="workflow.finish" and main[-1]["trace_id"]==a.trace_id
assert (t/"reports/WORKFLOW-CHRONOLOGY.md").is_file() and (t/"reports/WORKFLOW-TRACE.md").is_file()
dest.mkdir(parents=True)
entries={}
for folder in ["solution","baseline","bench","contracts","patches","reports","results"]:
    for path in sorted((t/folder).rglob("*")):
        if not path.is_file() or any(part in (".git","__pycache__","cache","backups") for part in path.relative_to(t).parts):continue
        rel=path.relative_to(t)
        if path.name.endswith(".trace.json"):continue
        if "captures" in rel.parts or "scratch" in rel.parts:continue
        if any(part.startswith("overlay-reconstruction-") for part in rel.parts):continue
        if str(rel) in ("results/workflow-delivery.jsonl","results/workflow-publication.jsonl"):continue
        if len(rel.parts)>=3 and rel.parts[:2]==("results","workflow-trace") and rel.parts[2]!=a.trace_id:continue
        if path.suffix in (".pyc",".so",".safetensors",".whl"):continue
        assert path.stat().st_size<50*1024*1024,(path,path.stat().st_size)
        target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
        entries[str(target.relative_to(repo))]=dict(bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
shutil.copy2(t/"README.md",dest/"README.md")
entries[str((dest/"README.md").relative_to(repo))]=dict(bytes=(dest/"README.md").stat().st_size,
    sha256=hashlib.sha256((dest/"README.md").read_bytes()).hexdigest())
manifest=dest/"DELIVERY-MANIFEST.json"
manifest.write_text(json.dumps(dict(trace_id=a.trace_id,source_task=str(t),files=entries,
    excludes=["all uncompressed *.trace.json; gzip archives preserve exact native trace bytes","large GEMM captures retained locally/on Thor with provenance","overlay reconstruction scratch directories","caches/binaries/checkpoints","local publication trace"]),
    ensure_ascii=False,indent=2)+"\n")
entries[str(manifest.relative_to(repo))]=dict(bytes=manifest.stat().st_size,sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())
with tempfile.NamedTemporaryFile() as f:
    f.write(b"".join(name.encode()+b"\0" for name in entries));f.flush()
    subprocess.run(["git","add","-f","--pathspec-from-file="+f.name,"--pathspec-file-nul"],cwd=repo,check=True)
staged=subprocess.check_output(["git","diff","--cached","--name-only","-z"],cwd=repo).decode().split("\0")
assert set(filter(None,staged))==set(entries),"Stage must exactly match manifest"
index=subprocess.check_output(["git","ls-files","--stage","-z","--",a.subdir],cwd=repo).decode().split("\0")
oids=[]
for value in index:
    if not value:continue
    meta,name=value.split("\t",1);mode,oid,stage=meta.split()
    assert stage=="0" and name in entries
    oids.append((oid,name))
data=subprocess.check_output(["git","cat-file","--batch"],cwd=repo,input=b"".join(oid.encode()+b"\n" for oid,name in oids))
offset=0
for oid,name in oids:
    end=data.index(b"\n",offset);header=data[offset:end].split();size=int(header[2]);offset=end+1
    blob=data[offset:offset+size];offset+=size+1
    assert header[0].decode()==oid and hashlib.sha256(blob).hexdigest()==entries[name]["sha256"],name
assert offset==len(data)
print(json.dumps(dict(destination=str(dest),staged_files=len(entries),index_sha256_all_match=True,
                     total_bytes=sum(v["bytes"] for v in entries.values())),ensure_ascii=False,indent=2))
