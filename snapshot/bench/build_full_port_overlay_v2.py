"""V4 additive overlay, actual fresh git-apply and byte comparison; includes V3 parents."""
from pathlib import Path
import argparse,difflib,hashlib,json,subprocess,tarfile
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
files=["solution/candidate-full-port-v3.py","solution/dynamic_lt_fallback_v3.py","solution/dynamic-lt-selected-v3.json","solution/candidate-full-port-v4.py","solution/opposite_layout_routes_v1.py","solution/main-layout-selected-v4.json","bench/dynamic_model_common_full_v3.py","bench/dynamic_model_common_full_v4.py","bench/validate_full_port_final_v4.py","bench/paired_full_port_v5.py","bench/validate_full_port_graph_v4.py","bench/profile_main_full_port_v4.py"]
patchdir=t/"patches";patchdir.mkdir(exist_ok=True)
patch=patchdir/"dynamic-full-port-v4-overlay.patch";assert not patch.exists()
body="".join("".join(difflib.unified_diff([], (t/rel).read_text().splitlines(keepends=True),fromfile="/dev/null",tofile="b/"+rel)) for rel in files)
patch.write_text(body)
rebuild=t/"results/overlay-reconstruction-v4";rebuild.mkdir()
subprocess.run(["git","apply",str(patch)],cwd=rebuild,check=True)
verified=[]
for rel in files:
    raw=(t/rel).read_bytes();assert raw==(rebuild/rel).read_bytes()
    verified.append(dict(path=rel,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
inventory=[]
for folder in ("solution","bench","baseline","contracts"):
    for src in sorted((t/folder).rglob("*")):
        if src.is_file() and not src.is_symlink() and "__pycache__" not in src.parts and ".git" not in src.parts and src.name!="final-source-inventory-v4.json":
            inventory.append(dict(path=str(src.relative_to(t)),bytes=src.stat().st_size,sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
(t/"contracts/final-source-inventory-v4.json").write_text(json.dumps(dict(files=inventory),indent=2)+"\n")
archive=patchdir/"dynamic-full-port-v4-sources.tar.gz";assert not archive.exists()
with tarfile.open(archive,"w:gz") as tar:
    for row in inventory:
        src=t/row["path"];info=tar.gettarinfo(str(src),arcname=row["path"])
        info.uid=info.gid=0;info.uname=info.gname="";info.mtime=0
        with src.open("rb") as f:tar.addfile(info,f)
doc=dict(complete=True,gate_passed=True,base="Inherited dynamic-v4 task solution/baseline directories; additive V3/V4 source overlay, full source archive also supplied",files=verified,patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),verification="Actual git apply in a fresh task-owned directory, then byte equality for every file",archive=dict(path=str(archive.relative_to(t)),bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
(t/"results/overlay-apply-audit-v4.json").write_text(json.dumps(doc,indent=2)+"\n")
print(json.dumps(dict(overlay_files=len(verified),source_files=len(inventory),patch_sha256=doc["patch_sha256"],archive=doc["archive"],actual_git_apply_passed=True),indent=2))
