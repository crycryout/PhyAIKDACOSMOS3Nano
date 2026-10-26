
"""Render every completed workflow event and recover only hash-matching read excerpts."""
from pathlib import Path
import argparse,collections,datetime,hashlib,json,shlex
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
trace=t/"results/workflow-trace.jsonl";events=[json.loads(l) for l in trace.read_text().splitlines()]
assert events and events[-1]["event"]=="workflow.finish","Render only a finished optimization trace"
reports=t/"reports";snaps=reports/"reads";snaps.mkdir(parents=True,exist_ok=True)
def rel(path):
    if not path:return ""
    try:return "../"+str(Path(path).relative_to(t))
    except ValueError:return str(path)
def stamp(text):
    utc=datetime.datetime.fromisoformat(text.replace("Z","+00:00"))
    return utc.astimezone(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="milliseconds")
counts=collections.Counter(e["event"] for e in events)
out=["# COSMOS3 动态迁移：逐事件完整时间线","",
     "以下按JSONL原始append顺序列出全部事件。展示UTC与澳门时间(UTC+8)，不把事件间隔当作GPU耗时。",
     "命令argv、日志hash、读取行段/内容hash和显式选择均来自实际Workflow Trace；不记录或推断隐藏思考。",
     "读取快照仅在当前文件选定行段仍与记录的SHA256完全一致时收录；已变化内容不冒充历史读取内容。","",
     "Trace ID: "+events[0]["trace_id"],"","事件统计："+json.dumps(counts,ensure_ascii=False),"",
     "## 按时间的全部事件",""]
read_index=[];recovered=0
for i,e in enumerate(events,1):
    kind=e["event"];out.extend([f"### {i:03d}. {stamp(e['time_utc'])} — {kind}","",
        "UTC: "+e["time_utc"]+"；event_id: "+e["event_id"],""])
    if kind=="workflow.read":
        target=e.get("payload_read",{});selection=e.get("payload_selection",{})
        out.extend(["目的："+str(e.get("payload_purpose","")),"",
            "来源："+str(e.get("payload_source",""))+"；capture_mode："+str(e.get("payload_capture_mode","")),
            "","路径："+str(target.get("path","")),"",
            "读取选择："+json.dumps(selection,ensure_ascii=False),"",
            "文件SHA256："+str(target.get("sha256"))+"；选段SHA256："+str(e.get("payload_content_sha256")),""])
        record=dict(event_id=e["event_id"],time_utc=e["time_utc"],path=target.get("path"),
                    selection=selection,purpose=e.get("payload_purpose"),source=e.get("payload_source"),
                    content_sha256=e.get("payload_content_sha256"),status=e.get("payload_status"))
        src=Path(target.get("path","/nonexistent"));excerpt=None
        if src.is_file() and isinstance(selection.get("line_start"),int):
            try:
                lines=src.read_text().splitlines(keepends=True)
                selected="".join(lines[selection["line_start"]-1:selection.get("line_end",len(lines))])
                if hashlib.sha256(selected.encode()).hexdigest()==e.get("payload_content_sha256"):
                    excerpt=selected
            except (OSError,UnicodeError):pass
        if excerpt is not None:
            path=snaps/(e["event_id"]+".md")
            path.write_text("# Observed read excerpt\n\n"+json.dumps(record,ensure_ascii=False,indent=2)+
                "\n\n"+chr(96)*3+"text\n"+excerpt+"\n"+chr(96)*3+"\n")
            record["verified_excerpt"]="reads/"+path.name;recovered+=1
            out.extend(["[哈希一致的读取快照](reads/"+path.name+")",""])
        else:
            record["verified_excerpt"]=None
            out.extend(["选段快照未恢复；以JSONL记录的当时hash与选段为准。",""])
        read_index.append(record)
    elif kind=="workflow.command.start":
        out.extend(["标签："+str(e.get("payload_label","")),"","目的："+str(e.get("payload_purpose","")),"",
                    "cwd："+str(e.get("payload_cwd","")),"",
                    "<details><summary>完整实际 argv</summary>","",chr(96)*3+"json",
                    json.dumps(e.get("payload_argv",[]),ensure_ascii=False,indent=2),chr(96)*3,"","</details>",""])
    elif kind=="workflow.command.finish":
        out.extend(["标签："+str(e.get("payload_label","")),"",
            f"退出码：{e.get('payload_returncode')}；耗时：{e.get('payload_elapsed_seconds')}秒；状态：{e.get('payload_status')}",
            "","对应start："+str(e.get("payload_command_start_event_id")),""])
        for stream in ["stdout","stderr"]:
            value=e.get("payload_"+stream,{})
            out.extend([f"{stream}: [{value.get('bytes')} bytes]({rel(value.get('path'))})；SHA256 {value.get('sha256')}",""])
    else:
        payload={k:v for k,v in e.items() if k.startswith("payload_")}
        out.extend([chr(96)*3+"json",json.dumps(payload,ensure_ascii=False,indent=2),chr(96)*3,""])
out.extend(["## 读取记录机器可读索引","",
    "[READ-INDEX.json](READ-INDEX.json)；共 "+str(len(read_index))+" 次读取，恢复 "+str(recovered)+" 个hash一致快照。",
    "已变化或未成功读取的选段不会以当前内容替换历史证据。",""])
(reports/"WORKFLOW-CHRONOLOGY.md").write_text("\n".join(out))
(reports/"READ-INDEX.json").write_text(json.dumps(read_index,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(dict(events=len(events),reads=len(read_index),verified_read_excerpts=recovered,
    chronology=str(reports/"WORKFLOW-CHRONOLOGY.md")),ensure_ascii=False,indent=2))
