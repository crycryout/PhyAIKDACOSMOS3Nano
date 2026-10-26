"""Validate release JSON and generated Markdown links without executing source."""
from pathlib import Path
import argparse,hashlib,json,re,urllib.parse
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);p.add_argument("--repo",type=Path);a=p.parse_args();t=a.task
checked=[];broken=[]
for path in sorted(t.rglob("*.json")):
    if any(part in ("__pycache__","cache",".git","captures","scratch") or part.startswith("overlay-reconstruction-") for part in path.relative_to(t).parts):continue
    if path.name.endswith(".trace.json"):continue
    json.loads(path.read_text());checked.append(str(path.relative_to(t)))
names=["README.md","reports/DYNAMIC-FULL-PORT.md","reports/DYNAMIC-FULL-PORT-V3.md","reports/DYNAMIC-ROUTE-MAP.md","reports/SUPPLEMENTARY-EXPERIMENTS.md","reports/WORKFLOW-CHRONOLOGY.md","reports/READ-PROVENANCE.md","reports/EXPERIMENT-TIMELINE.md"]
links=[]
for name in names:
    path=t/name;assert path.is_file(),name
    body=path.read_text();in_fence=False
    for number,line in enumerate(body.splitlines(),1):
        if re.match(r"^\s*(?:`{3,}|~{3,})",line):in_fence=not in_fence;continue
        if in_fence:continue
        for value in re.findall('!?\\[[^\\]]*\\]\\(([^)]+)\\)',line):
            value=value.split("#",1)[0].strip("<>")
            if not value or re.match(r"^[a-zA-Z]+://",value) or value.startswith("mailto:"):continue
            dst=(path.parent/urllib.parse.unquote(value)).resolve()
            exists=dst.exists()
            if not exists and value.startswith("../../") and a.repo is not None:
                dst=(a.repo/"examples"/Path(value).relative_to("../..")).resolve();exists=dst.exists()
            links.append(dict(source=name,line=number,target=value,exists=exists))
            if not exists:broken.append(links[-1])
doc=dict(complete=True,gate_passed=not broken,json_files_checked=len(checked),markdown_links_checked=len(links),broken=broken)
(t/"results/delivery-document-audit-v4.json").write_text(json.dumps(doc,indent=2)+"\n")
print(json.dumps(doc,indent=2))
assert not broken,broken
