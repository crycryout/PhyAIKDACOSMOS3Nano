"""Export observable workflow evidence; do not infer unrecorded reasoning or reads."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse, collections, hashlib, json, shlex
p=argparse.ArgumentParser()
p.add_argument("--trace",type=Path,required=True)
p.add_argument("--out",type=Path,required=True)
a=p.parse_args();out=a.out;out.mkdir(parents=True,exist_ok=True)
rows=[json.loads(line) for line in a.trace.read_text().splitlines() if line.strip()]
reads=[];commands=[];snapshots=out/"reads";snapshots.mkdir(exist_ok=True)
command_dir=out/"commands";command_dir.mkdir(exist_ok=True)
task=a.trace.parent.parent
hash_sources=collections.defaultdict(list)
for folder in ("reports","bench","contracts","solution"):
    for candidate in sorted((task/folder).rglob("*")):
        if candidate.is_file() and not candidate.is_symlink() and candidate.stat().st_size<2*1024*1024 and "__pycache__" not in candidate.parts:
            hash_sources[hashlib.sha256(candidate.read_bytes()).hexdigest()].append(candidate)

md=["# 动态完整迁移：逐事件可观察时间线","","来源为完成后的 append-only Workflow Trace。UTC 与澳门时间（UTC+8）并列；时间线记录显式目的、工具输出元数据和选择，不声称读取隐藏思考。读取快照仅在选定内容精确匹配当时selection SHA256时重建；另记录原文件全量SHA是否仍匹配。全量文件已变但选择未变会明确标记，不匹配的历史读取不补造。","",f"Trace: `{rows[0]['trace_id']}`；源事件数：{len(rows)}。","","本轮没有派生子 Agent；历史多 Agent 的记录见上轮 chronology 独立目录。","" ]
for n,r in enumerate(rows,1):
    event=r["event"];eid=r["event_id"]
    dt=datetime.fromisoformat(r["time_utc"].replace("Z","+00:00"))
    local=dt.astimezone(ZoneInfo("Asia/Macao")).isoformat(timespec="milliseconds")
    md.extend([f"## {n:04d}. {r['time_utc']} / 澳门 {local}","",f"事件 `{event}`；ID `{eid}`。",""])
    if event=="workflow.read":
        ref=r.get("payload_read",{});sel=r.get("payload_selection",{});src=Path(ref.get("path","/nonexistent"))
        rec=dict(event_id=eid,time_utc=r["time_utc"],time_macao=local,source=r.get("payload_source"),purpose=r.get("payload_purpose"),status=r.get("payload_status"),capture_mode=r.get("payload_capture_mode"),path=str(src),selection=sel,file_sha256=ref.get("sha256"),selection_sha256=r.get("payload_content_sha256"),snapshot_status="unavailable")
        recovered=hash_sources.get(ref.get("sha256"),[])
        readable=not any(x in str(src) for x in ("/.ssh/","/sessions/","auth.json"))
        material=src if readable and src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest()==ref.get("sha256") else (recovered[0] if readable and recovered else src)
        if r.get("payload_status")=="completed" and r.get("payload_capture_mode")=="tool_output" and material.is_file() and not any(x in str(src) for x in ("/.ssh/","/sessions/","auth.json")):
            raw=material.read_bytes()
            rec["reconstruction_source"]=str(material)
            rec["reconstruction_from_matching_archived_file"]=material!=src
            rec["current_source_sha256"]=hashlib.sha256(src.read_bytes()).hexdigest() if src.is_file() else None
            rec["reconstruction_source_sha256"]=hashlib.sha256(raw).hexdigest()
            rec["full_source_hash_still_matches"]=src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest()==ref.get("sha256")
            rec["reconstruction_file_sha256_matches"]=hashlib.sha256(raw).hexdigest()==ref.get("sha256")
            if True:  # Only the exact observed selection hash authorizes a reconstructed snapshot.
                text=raw.decode("utf-8");first=sel.get("line_start",1);last=sel.get("line_end",len(text.splitlines()))
                selected="".join(text.splitlines(keepends=True)[first-1:last])
                candidates=[selected,selected.rstrip("\n"),selected.rstrip("\n")+"\n",text]
                exact=next((x for x in candidates if hashlib.sha256(x.encode()).hexdigest()==r.get("payload_content_sha256")),None)
                if exact is not None:
                    rec["snapshot_status"]=("verified_from_archived_full_source_and_observed_selection_hash" if material!=src else "verified_against_observed_selection_hash" if rec["full_source_hash_still_matches"] else "verified_observed_selection_hash_full_source_changed")
                    rec["source_change_note"]=("Archived full source SHA256 and observed selection SHA256 both match; original path has changed." if material!=src else "Full source still matches at export." if rec["full_source_hash_still_matches"] else "Full source changed; this selected text still exactly matches the observed historical selection SHA256.")
                    rec["snapshot"]="reads/"+eid+".md"
                    fence="`"*(max([len(part) for part in exact.split() if part and set(part)=={"`"}]+[3])+1)
                    (snapshots/(eid+".md")).write_text("# 读取快照\n\n"+json.dumps(rec,ensure_ascii=False,indent=2)+"\n\n"+fence+"text\n"+exact+"\n"+fence+"\n")
                else:rec["snapshot_status"]="observed_selection_cannot_be_reconstructed_from_current_source"
            else:rec["snapshot_status"]="source_changed_since_read_do_not_backfill"
        elif r.get("payload_capture_mode")=="agent_declared":rec["snapshot_status"]="agent_declared_reference_not_observed_read"
        elif r.get("payload_status")=="failed":rec["snapshot_status"]="failed_read_no_content_claim"
        reads.append(rec)
        md.extend([f"读取来源：{rec['source']}；状态：{rec['status']}；捕获：{rec['capture_mode']}。","",f"目的：{rec['purpose']}","",f"路径：`{src}`；行段：`{sel.get('line_start','?')}–{sel.get('line_end','?')}`；声明章节：{sel.get('section','')}。","",f"文件 SHA256：`{rec['file_sha256']}`；选择 SHA256：`{rec['selection_sha256']}`。",""])
        md.extend([f"快照：[已核对字节]({rec['snapshot']})。" if "snapshot" in rec else "快照状态："+rec["snapshot_status"]+"。",""])
        if r.get("payload_error"):md.extend(["错误："+r["payload_error"],""])
    elif event.startswith("workflow.command."):
        detail=command_dir/(eid+".json");detail.write_text(json.dumps(r,ensure_ascii=False,indent=2)+"\n")
        rec=dict(event_id=eid,time_utc=r["time_utc"],event=event,label=r.get("payload_label"),purpose=r.get("payload_purpose"),argv=r.get("payload_argv"),cwd=r.get("payload_cwd"),status=r.get("payload_status"),returncode=r.get("payload_returncode"),elapsed_seconds=r.get("payload_elapsed_seconds"),command_start_event_id=r.get("payload_command_start_event_id"),stdout=r.get("payload_stdout"),stderr=r.get("payload_stderr"))
        commands.append(rec)
        md.extend([f"命令标签：`{rec['label']}`。目的：{rec['purpose']}","",f"工作目录：`{rec['cwd']}`；状态：`{rec['status']}`；退出码：`{rec['returncode']}`；持续秒数：`{rec['elapsed_seconds']}`。","",f"[完整 argv、日志路径及哈希](commands/{eid}.json)。",""])
    else:
        payload={k.removeprefix("payload_"):v for k,v in r.items() if k.startswith("payload_")}
        md.extend(["```json",json.dumps(payload,ensure_ascii=False,indent=2),"```",""])
(out/"WORKFLOW-CHRONOLOGY.md").write_text("\n".join(md))
(out/"read-provenance.json").write_text(json.dumps(reads,ensure_ascii=False,indent=2)+"\n")
(out/"command-provenance.json").write_text(json.dumps(commands,ensure_ascii=False,indent=2)+"\n")
index=["# Agent 读取来源与具体行段","","tool_output 表示工具输出了选定内容；agent_declared 仅为声明；失败读取不主张读到了内容。","","| UTC | 来源 / 目的 | 路径 / 行段 | 捕获 / 状态 | 选择 SHA256 / 快照 |","| --- | --- | --- | --- | --- |"]
for r in reads:
    clean=lambda x:str(x).replace("|","\|").replace("\n"," ")
    snapshot=f"[字节快照]({r['snapshot']})" if "snapshot" in r else r["snapshot_status"]
    index.append(f"| {r['time_utc']} | {clean(r['source'])}<br>{clean(r['purpose'])} | `{clean(r['path'])}`<br>{r['selection'].get('line_start','?')}–{r['selection'].get('line_end','?')} | {r['capture_mode']} / {r['status']} | `{r['selection_sha256']}`<br>{snapshot} |")
(out/"READ-PROVENANCE.md").write_text("\n".join(index)+"\n")
summary=dict(events=len(rows),reads=len(reads),verified_read_snapshots=sum("snapshot" in r for r in reads),command_events=len(commands),event_types=dict(collections.Counter(r["event"] for r in rows)),source_trace_sha256=hashlib.sha256(a.trace.read_bytes()).hexdigest())
(out/"chronology-index.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps(summary,indent=2))
