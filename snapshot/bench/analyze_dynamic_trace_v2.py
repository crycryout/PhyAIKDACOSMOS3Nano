"""Correlate actual CUDA kernels to explicit CPU scopes in one native Torch trace."""
from pathlib import Path
import argparse,bisect,collections,csv,hashlib,json
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
src=t/"results/profile-v4/candidate-dynamic.trace.json";out=t/"results/profile-analysis-v4"
ev=json.loads(src.read_text())["traceEvents"]
scopes=[e for e in ev if e.get("cat")=="user_annotation" and e.get("ph")=="X"]
def index(prefix):
    groups=collections.defaultdict(list)
    for e in scopes:
        if e["name"].startswith(prefix):groups[(e["pid"],e["tid"])].append(e)
    return {key:(sorted(v,key=lambda e:e["ts"]),sorted(e["ts"] for e in v)) for key,v in groups.items()}
indexes={kind:index(prefix) for kind,prefix in [
    ("gen_gemm","cosmos3_GEN_GEMM/"),("gen_attention","cosmos3_GEN_ATTENTION/"),
    ("stage","cosmos3_stage/")]}
def find(rt,kind):
    rows,starts=indexes[kind].get((rt["pid"],rt["tid"]),([],[]))
    pos=bisect.bisect_right(starts,rt["ts"])-1
    if pos>=0:
        row=rows[pos]
        if rt["ts"]<=row["ts"]+row["dur"]:return row["name"]
    return None
runtime=collections.defaultdict(list)
for e in ev:
    if e.get("cat") in ("cuda_runtime","cuda_driver") and "correlation" in e.get("args",{}):
        runtime[e["args"]["correlation"]].append(e)
kernels=[e for e in ev if e.get("cat")=="kernel" and e.get("ph")=="X"]
rows=[];stages=collections.defaultdict(lambda:dict(count=0,kernel_sum_us=0.))
for k in kernels:
    hosts=runtime.get(k.get("args",{}).get("correlation"),[])
    owners={kind:next((value for rt in hosts if (value:=find(rt,kind)) is not None),None)
            for kind in indexes}
    kind="gen_gemm" if owners["gen_gemm"] else "gen_attention" if owners["gen_attention"] else "other"
    row=dict(kernel=k["name"],ts_us=k["ts"],dur_us=k["dur"],stream=k["args"].get("stream"),
        owner_kind=kind,scope=owners.get(kind),stage=owners["stage"],
        correlation=k.get("args",{}).get("correlation"))
    rows.append(row)
    stage=owners["stage"] or "unattributed"
    stages[stage]["count"]+=1;stages[stage]["kernel_sum_us"]+=k["dur"]
def union_us(events):
    intervals=sorted((e["ts"],e["ts"]+e["dur"]) for e in events if e.get("dur",0)>0)
    if not intervals:return 0.
    begin,end=intervals[0];total=0.
    for left,right in intervals[1:]:
        if left>end:total+=end-begin;begin,end=left,right
        else:end=max(end,right)
    return total+end-begin
counts=collections.Counter(r["owner_kind"] for r in rows)
scope_counts={kind:sum(len(v[0]) for v in idx.values()) for kind,idx in indexes.items()}
assert scope_counts["gen_gemm"]==1152 and scope_counts["gen_attention"]==288,scope_counts
v40=[k for k in kernels if "PV144V40" in k["name"]]
assert counts["gen_gemm"]==1152 and len(v40)==288,(counts,len(v40))
aggregate=collections.defaultdict(lambda:dict(launches=0,sum_us=0.))
for row in rows:
    value=aggregate[row["kernel"]];value["launches"]+=1;value["sum_us"]+=row["dur_us"]
top=sorted((dict(kernel=name,**value) for name,value in aggregate.items()),key=lambda r:r["sum_us"],reverse=True)
summary=dict(complete=True,trace_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
    kernel_launches=len(kernels),kernel_duration_sum_ms=sum(k["dur"] for k in kernels)/1000,
    kernel_busy_union_ms=union_us(kernels)/1000,
    gpu_activity_busy_union_ms=union_us([e for e in ev if e.get("cat") in ("kernel","gpu_memcpy","gpu_memset")])/1000,
    attributed_launches=dict(counts),v40_attention_main_kernel_launches=len(v40),
    v40_attention_main_kernel_sum_ms=sum(k["dur"] for k in v40)/1000,explicit_cpu_scope_counts=scope_counts,
    gen_gemm_sum_ms=sum(r["dur_us"] for r in rows if r["owner_kind"]=="gen_gemm")/1000,
    gen_attention_sum_ms=sum(r["dur_us"] for r in rows if r["owner_kind"]=="gen_attention")/1000,
    by_stage=dict(stages),top_kernels=top,
    interpretation="kernel duration sum, busy union, and unprofiled ready-wall E2E are different quantities; no causal speedup or MFU inferred",
    workflow_heuristic_correction="the v40 Sm100Fmha kernel is attention; generic tool's memory label is heuristic",
    mapping="CUDA kernel correlation -> CUDA runtime/driver event -> same-thread explicit CPU scope")
(out/"same-trace-physical-attribution.json").write_text(json.dumps(summary,indent=2)+"\n")
with (out/"same-trace-kernel-attribution.csv").open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
md=["# Dynamic request: physical kernel attribution","",summary["mapping"],"",
    "| Quantity | Observed |","| --- | ---: |",
    "| GEN GEMM scopes / CUDA kernels | 1152 / 1152 |",
    f"| GEN attention scopes / v40 main kernels | 288 / {len(v40)} |",
    f"| All CUDA kernels inside GEN attention scopes | {counts['gen_attention']} |",
    f"| All kernel launches | {len(kernels)} |",
    f"| Summed kernel duration | {summary['kernel_duration_sum_ms']:.3f} ms |",
    f"| Kernel busy interval union | {summary['kernel_busy_union_ms']:.3f} ms |",
    f"| GPU activity busy interval union | {summary['gpu_activity_busy_union_ms']:.3f} ms |",
    f"| GEN GEMM duration sum | {summary['gen_gemm_sum_ms']:.3f} ms |",
    f"| GEN attention duration sum | {summary['gen_attention_sum_ms']:.3f} ms |","",
    summary["interpretation"],"",summary["workflow_heuristic_correction"],"",
    "| GPU stage | Kernels | Sum (ms) |","| --- | ---: | ---: |"]
for name,v in stages.items():md.append(f"| {name} | {v['count']} | {v['kernel_sum_us']/1000:.3f} |")
md+=["","No overlap or fusion savings are established by this candidate-only trace. Full workflow three-table output is preserved separately.",""]
(out/"SAME-TRACE-ATTRIBUTION.md").write_text("\n".join(md))
print(json.dumps({k:v for k,v in summary.items() if k not in ("top_kernels",)},indent=2))
