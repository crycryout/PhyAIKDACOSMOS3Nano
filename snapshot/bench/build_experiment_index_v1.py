"""Build an observed experiment index from actual immutable Thor run records."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,json
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
rows=[]
def rel(p):return str(p.relative_to(t))
for path in sorted((t/"results").glob("*/run.json")):
    d=json.loads(path.read_text());folder=path.parent
    start=d.get("before",{}).get("utc")
    if not start:continue
    row=dict(tag=folder.name,start_utc=start,end_utc=d.get("after",{}).get("utc"),returncode=d.get("returncode"),interference_observed=d.get("interference_observed"),profile=d.get("profile"),workflow_event_id=d.get("workflow_event_id"),run=rel(path),argv=d.get("argv"),evidence=[])
    for name in ("validation.json","graph-fallback-validation.json","paired-full-port-e2e.json","independent-screen-audit.json","profile-metadata.json"):
        f=folder/name
        if not f.is_file():continue
        data=json.loads(f.read_text());e=dict(path=rel(f),complete=data.get("complete"))
        for key in ("exact_gate_passed","gate_passed","all_bytes_phases_dispatch_passed","byte_equal","summary","screen_only"):
            if key in data:e[key]=data[key]
        for key in ("cases","pairs","rows"):
            if isinstance(data.get(key),list):e[key+"_count"]=len(data[key])
        if name=="independent-screen-audit.json":
            e["results"]=data.get("results",[])
        row["evidence"].append(e)
    rows.append(row)
rows.sort(key=lambda r:(r["start_utc"],r["tag"]))
md=["# COSMOS3动态迁移：全部实际Thor运行索引","","按run.json实测开始时间排序。失败、退化和非晋升实验全部保留；退出码0仅说明进程完成，数值/性能门槛由各独立audit决定。UTC与澳门UTC+8并列；所有筛选收益相对其各自baseline，不自动混算成官方总收益。","",f"实际远程运行记录共{len(rows)}份。完整读取、命令和选择事件见[Workflow逐事件时间线](WORKFLOW-CHRONOLOGY.md)。",""]
for i,r in enumerate(rows,1):
    dt=datetime.fromisoformat(r["start_utc"].replace("Z","+00:00"))
    local=dt.astimezone(ZoneInfo("Asia/Macao")).isoformat(timespec="seconds")
    md += [f"## {i:03d}. {r['tag']}","",f"开始UTC：{r['start_utc']}；澳门：{local}；结束UTC：{r['end_utc']}。","",f"退出码：{r['returncode']}；外来GPU干扰：{r['interference_observed']}；profile：{r['profile']}。","",f"实际命令、身份、遥测、日志：[run.json](../{r['run']})；Workflow start event：{r['workflow_event_id']}。",""]
    for e in r["evidence"]:
        md += [f"证据：[本次{Path(e['path']).name}](../{e['path']})","","\u0060\u0060\u0060json",json.dumps({k:v for k,v in e.items() if k!="path"},ensure_ascii=False,indent=2),"\u0060\u0060\u0060",""]
(t/"reports/EXPERIMENT-TIMELINE.md").write_text("\n".join(md)+"\n")
(t/"reports/experiment-index.json").write_text(json.dumps(dict(complete=True,runs=rows),ensure_ascii=False,indent=2)+"\n")
print(json.dumps(dict(runs=len(rows),failed=sum(r["returncode"] not in (None,0) for r in rows),report=str(t/"reports/EXPERIMENT-TIMELINE.md")),ensure_ascii=False,indent=2))
