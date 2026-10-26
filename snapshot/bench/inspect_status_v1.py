"""Read-only bounded Thor progress snapshots for this task; no GPU work."""
from pathlib import Path
import argparse
import datetime
import json
import shlex
import subprocess
p=argparse.ArgumentParser()
p.add_argument("--remote-root",required=True)
p.add_argument("--out",type=Path,required=True)
p.add_argument("paths",nargs="+")
a=p.parse_args()
code=r'''
from pathlib import Path
import json,sys
root=Path(sys.argv[1]);assert not root.is_symlink()
root=root.resolve();assert root.is_relative_to(Path("/home/tomorin/rjc").resolve())
rows=[]
for rel in json.loads(sys.argv[2]):
 p=(root/rel).resolve();assert p.is_relative_to(root)
 row={"path":rel,"exists":p.is_file()}
 if p.is_file():
  if p.suffix==".json":
   try:
    d=json.loads(p.read_text())
    if "results" in d and d.get("screen_only"):
     row.update(complete=d.get("complete"),rows=len(d.get("rows",[])),results=[{k:r[k] for k in ["case","M","category","paired_median_reduction_pct","reduction_from_total_time_pct","accepted"] if k in r} | {"pairs":len(r.get("pairs",[]))} for r in d["results"]])
    elif "shapes" in d:
     row.update(complete=d.get("complete"),shapes=[{"case":r["case"],"category":r["category"],"M":r["shape"][0],"tested":len(r["candidates"]),"selected_ratio":(r.get("selected") or {}).get("ratio_to_torch_mm")} for r in d["shapes"]])
    elif "exact_gate_passed" in d:
     row.update(complete=d["complete"],gate=d["exact_gate_passed"],cases=[{"case":r["case"],"byte_equal":r["byte_equal"],"ms":r["ready_wall_ms"],"dynamic_lt":r.get("optimization",{}).get("dynamic_lt_extension",{}).get("counters",{})} for r in d["cases"]])
    elif "pairs" in d and "summary" in d:
     row.update(complete=d["complete"],gate=d.get("gate_passed"),pair_count=len(d["pairs"]),last_pair=d["pairs"][-1] if d["pairs"] else None,summary=d["summary"],calibration=d.get("calibration"))
    elif p.name=="run.json":
     row.update(returncode=d.get("returncode"),interference=d.get("interference_observed"))
    else:row["json"]=d
   except (ValueError,KeyError) as error:row["read_error"]=str(error)
  else:row["tail"]=p.read_text(errors="replace")[-2500:]
 rows.append(row)
print(json.dumps(rows))
'''
ssh=["docker","exec","-i","thor-bridge","ssh","-T","-o","BatchMode=yes","-o","StrictHostKeyChecking=yes","-o","ConnectTimeout=15","-o","ServerAliveInterval=15","-o","ServerAliveCountMax=4","tomorin@172.30.3.112"]
r=subprocess.run([*ssh,shlex.join(["python3","-B","-c",code,a.remote_root,json.dumps(a.paths)])],capture_output=True,text=True,timeout=120)
if r.returncode:
 print(r.stderr);raise SystemExit(r.returncode)
rows=json.loads(r.stdout)
result={"observed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"remote_root":a.remote_root,"rows":rows}
a.out.parent.mkdir(parents=True,exist_ok=True)
with a.out.open("x") as f:json.dump(result,f,indent=2);f.write("\n")
print(json.dumps(result,indent=2))
