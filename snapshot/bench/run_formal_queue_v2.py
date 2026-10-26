"""Task-owned serial queue; every work stage retains its own Workflow command lifecycle."""
from pathlib import Path
import argparse,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--task",type=Path,required=True);p.add_argument("--remote-root",required=True);p.add_argument("--trace",required=True);p.add_argument("--trace-id",required=True);a=p.parse_args()
base=[sys.executable,"tools/workflow_trace.py","run","--trace-file",a.trace,"--trace-id",a.trace_id]
remote=[sys.executable,"tools/thor.py","run","--task-root",a.remote_root]
ref=a.remote_root+"/results/official-fresh-v1"
stages=[]
for family,pairs,cases in [("main",20,["len31_17","len65_97","len128_129","len257_7"]),("shapes",21,["video320x512","video17frames","action16"])]:
    for window in [0,1]:
        tag=f"formal-{family}-v3-window{window}"
        args=["--backend","candidate","--baseline","official","--pairs",str(pairs),"--window-index",str(window),"--reference",ref,"--out",a.remote_root+"/results/"+tag]
        for case in cases:args.extend(["--case",case])
        stages.append((tag,f"独立进程正式{family}窗口{window}，{pairs}对官方/最终V3，A/A校准和每请求BF16 byte gate","paired_full_port_v4.py",args))
stages.extend([("graph-fallback-full-port-v3","最终V3真实官方Graph oracle与动态长度切换回退逐字节验证","validate_full_port_graph_v3.py",["--backend","candidate","--cuda-graph","--reference",ref,"--out",a.remote_root+"/results/graph-fallback-full-port-v3"]),("profile-full-port-v3","最终V3独立候选完整请求CPU+CUDA原生trace，归因与未profile计时分开","profile_full_port_v3.py",["--backend","candidate","--reference",ref,"--out",a.remote_root+"/results/profile-full-port-v3"])])
queue=a.task/"results/formal-queue-v2.json"
doc=dict(complete=False,stages=[])
def save():queue.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n")
assert not queue.exists();save()
for tag,purpose,harness,args in stages:
    cmd=base+["--label",tag,"--purpose",purpose,"--"]+remote+["--tag",tag,"--","timeout","1200","/bin/bash","bench/run_dynamic_v3.sh",harness]+args
    entry=dict(tag=tag,purpose=purpose,argv=cmd,complete=False);doc["stages"].append(entry);save()
    print(json.dumps(dict(queue_stage_start=tag),ensure_ascii=False),flush=True)
    proc=subprocess.run(cmd,cwd=a.root)
    entry.update(complete=True,returncode=proc.returncode);save()
    print(json.dumps(dict(queue_stage_finish=tag,returncode=proc.returncode)),flush=True)
    if proc.returncode:sys.exit(proc.returncode)
doc["complete"]=True;save()
