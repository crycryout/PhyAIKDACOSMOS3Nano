"""Plot every unprofiled adjacent main-workload pair without filtering."""
from pathlib import Path
import argparse,csv,hashlib,json,statistics
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
out=t/"reports/figures";out.mkdir(parents=True,exist_ok=True)
fig,axes=plt.subplots(2,2,figsize=(12,7),sharex="col",layout="constrained")
all_pairs=[]
for w in (0,1):
    d=json.loads((t/f"results/formal-main-v3-window{w}/paired-full-port-e2e.json").read_text())
    assert d["complete"] and d["gate_passed"] and len(d["pairs"])==20
    rows=d["pairs"];all_pairs.extend(rows)
    x=[r["pair"]+1 for r in rows]
    baseline=[r["baseline_ms"]/1000 for r in rows];candidate=[r["candidate_ms"]/1000 for r in rows]
    reduction=[100*(1-c/b) for b,c in zip(baseline,candidate)]
    ax=axes[0,w];ax.plot(x,baseline,"o-",color="#626d78",label="Official",linewidth=1.3,markersize=4)
    ax.plot(x,candidate,"o-",color="#1177bb",label="Final dynamic V3",linewidth=1.3,markersize=4)
    ax.set(title=f"Window {w}: separate model process",ylabel="Ready GPU action E2E (s)")
    ax.legend(loc="best");ax.grid(alpha=.2)
    ax=axes[1,w];ax.plot(x,reduction,color="#758797",linewidth=1)
    ax.scatter(x,reduction,c=["#db7336" if y<30 else "#147e70" for y in reduction],s=24,zorder=3)
    ax.axhline(30,color="#bd4545",linestyle="--",label="30% reference")
    ax.axhline(statistics.median(reduction),color="#147e70",linestyle=":",label=f"Paired median: {statistics.median(reduction):.2f}%")
    ax.set(xlabel="Adjacent AB/BA pair index (all 20 pairs)",ylabel="Latency reduction (%)",xticks=[1,5,10,15,20])
    ax.legend(loc="best");ax.grid(alpha=.2)
fig.suptitle("COSMOS3 Nano BF16: dynamic language inputs, cold UND, online VAE included",fontsize=13)
fig.savefig(out/"main-paired-latency.png",dpi=170)
fig.savefig(out/"main-paired-latency.svg")
plt.close(fig)
with (out/"main-paired-latency.csv").open("w",newline="") as f:
    fields=["window","pair","case","baseline_ms","candidate_ms","reduction_pct","order"]
    writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");writer.writeheader();writer.writerows(all_pairs)
meta=dict(complete=True,matplotlib_version=matplotlib.__version__,all_pairs_plotted=len(all_pairs),filtered_samples=0,excluded_from_plot="Warmup and A/A shown separately in raw evidence; no profiler times",files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob("main-paired-latency.*")})
(out/"plot-provenance.json").write_text(json.dumps(meta,indent=2)+"\n")
print(json.dumps(meta,indent=2))
