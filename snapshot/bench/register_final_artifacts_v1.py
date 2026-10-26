"""Register reviewable final artifacts into the active append-only Trace."""
from pathlib import Path
import argparse,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--task",type=Path,required=True);p.add_argument("--trace",required=True);p.add_argument("--trace-id",required=True);a=p.parse_args();t=a.task
paths=[
("source","solution/candidate-full-port-v4.py"),("source","solution/opposite_layout_routes_v1.py"),
("contract","contracts/formal-measurement-v4.json"),("source-hashes","contracts/full-port-v4-frozen-hashes-v2.json"),("source-hashes","contracts/final-source-inventory-v4.json"),
("patch","patches/dynamic-full-port-v4-overlay.patch"),("source-archive","patches/dynamic-full-port-v4-sources.tar.gz"),("evidence","results/overlay-apply-audit-v4.json"),
("precision","results/candidate-gate-v4/validation.json"),("precision","results/full-model-independent-audit-v4.json"),("precision","results/extra-main-independent-audit-v4.json"),
("independent-audit","results/final-independent-audit-v4.json"),("runtime-audit","results/release-runtime-audit-v4.json"),("route-audit","results/formal-route-audit-v4.json"),
("result","results/final-outcome-v4.json"),("graph-evidence","results/graph-fallback-full-port-v4/graph-fallback-validation.json"),
("profile-evidence","results/profile-main-full-port-v4/profile-metadata.json"),("native-trace","results/profile-main-full-port-v4/candidate-dynamic.trace.json.gz"),
("independent-audit","results/graph-profile-independent-audit-v4.json"),("archive-audit","results/native-trace-archive-audit-v4.json"),("attribution","results/profile-analysis-main-v4/same-trace-physical-attribution.json"),
("analysis","results/profile-analysis-main-v4/WORKFLOW-THREE-TABLES.md"),("analysis","results/profile-analysis-main-v4/SAME-TRACE-ATTRIBUTION.md"),
("figure","reports/figures/plot-provenance-v4.json"),("samples","reports/figures/main-paired-latency-v4.csv"),
("report","reports/DYNAMIC-FULL-PORT.md"),("report","reports/DYNAMIC-FULL-PORT-V3.md"),("report","reports/SUPPLEMENTARY-EXPERIMENTS.md"),
("source-map","reports/DYNAMIC-ROUTE-MAP.md"),("chronology","reports/EXPERIMENT-TIMELINE.md"),("chronology-index","reports/experiment-index.json")]
for family in ("main","shapes"):
    for window in (0,1):
        tag=f"formal-{family}-v4-window{window}"
        for filename in ("paired-full-port-e2e.json","run.json","runtime-source-hashes.json","runtime-binary-hashes.json"):
            paths.append(("formal-evidence",f"results/{tag}/{filename}"))
for role,rel in paths:
    path=t/rel;assert path.is_file(),path
    subprocess.run([sys.executable,str(a.root/"tools/workflow_trace.py"),"artifact","--trace-file",a.trace,"--trace-id",a.trace_id,"--role",role,"--note","Final V4 dynamic full-port delivery; raw failures and full command logs retained in task manifest","--path",str(path)],cwd=a.root,check=True,stdout=subprocess.DEVNULL)
print(json.dumps(dict(registered=len(paths),paths=[rel for role,rel in paths]),indent=2))
