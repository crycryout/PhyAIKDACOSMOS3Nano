"""Adjacent unprofiled full E2E; raw per-request byte gates and A/A calibration."""
from dynamic_model_common_full_v4 import *
import statistics

p = parser()
p.add_argument("--baseline", choices=["official", "parent_dynamic"], default="official")
p.add_argument("--calibration-pairs", type=int, default=4)
p.add_argument("--window-index", type=int, choices=[0,1])
a = p.parse_args()
window_indices = [a.window_index] if a.window_index is not None else [0,1]
assert a.reference is not None and not a.cuda_graph
assert a.pairs >= 1
engine, vae, vae_runner, counts = setup(a)
control = None
doc = dict(complete=False, gate_passed=False, baseline=a.baseline, candidate="full_dynamic",
           boundary="GPU pixels -> online VAE -> original engine.step -> ready GPU BF16 action",
           condition_regime="cold UND per request, 2 encoded CFG branches",
           quality="exact BF16 storage bytes versus independently archived original official",
           warmup="2 untimed full requests for every measured mode and shape",
           order="adjacent AB/BA; parity reverses in second window",
           calibration=[], rows=[], pairs=[], summary={}, window_indices=window_indices,
           independent_process_window=a.window_index)
save(a.out / "paired-full-port-e2e.json", doc)

def configure(label):
    control.dynamic_lt.set_enabled(label == "full_dynamic")
    control.set_main_enabled(label == "full_dynamic")
    control.set_mode("official" if label == "official" else "candidate")

def clear_conditions():
    runner = engine.entry.scheduler.runner
    runner.reset()
    runner._condition_cache.clear()

def sample(label, case, window, index, calibration=False):
    name, pixels, request, use_stream, metadata = case
    assert not use_stream and not metadata["same_cfg"]
    configure(label)
    clear_conditions()
    output, row = measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
    idle()
    equal = bool(torch.equal(output.contiguous().view(torch.uint8), refs[name].contiguous().view(torch.uint8)))
    row.update(window=window,pair=index,case=name,backend=label,calibration=calibration,
               byte_equal=equal,workload=metadata,
               optimization=dict(control.last_request_stats) if label!="official" else None)
    doc["rows"].append(row)
    save(a.out / "paired-full-port-e2e.json",doc)
    emit("measured_full_port",**row)
    assert equal,("Independent BF16 byte gate",label,name,row)
    assert row["phase_counts"].get("condition_encode")==2,row
    return row

def summarize(pairs):
    bs=[r["baseline_ms"] for r in pairs];cs=[r["candidate_ms"] for r in pairs]
    return dict(samples=len(pairs),baseline_median_ms=statistics.median(bs),candidate_median_ms=statistics.median(cs),
                reduction_from_medians_pct=100*(1-statistics.median(cs)/statistics.median(bs)),
                paired_median_reduction_pct=statistics.median(r["reduction_pct"] for r in pairs),
                reduction_from_total_time_pct=100*(1-sum(cs)/sum(bs)),
                all_bytes_equal=True)

try:
    matrix=cases(a)
    control=install(engine,vae)
    control.audit_proof=False;control.audit_pure=False;control.audit_signature=False
    refs={name:torch.load(a.reference/"actions"/(name+".pt"),map_location="cuda",weights_only=True)
          for name,_,_,_,_ in matrix}
    for label in [a.baseline,"full_dynamic"]:
        configure(label)
        for name,pixels,request,use_stream,metadata in matrix:
            for index in range(2):
                clear_conditions()
                _,row=measured(lambda:control.full(pixels,request,vae_runner,engine),counts,request)
                emit("warmup_full_port",backend=label,case=name,index=index,ready_wall_ms=row["ready_wall_ms"])
    for window in window_indices:
        aa=[]
        if a.baseline=="official":
            for index in range(a.calibration_pairs):
                case=matrix[index%len(matrix)]
                left=sample("official",case,window,index,True)
                right=sample("official",case,window,index,True)
                aa.append(dict(case=case[0],first_ms=left["ready_wall_ms"],second_ms=right["ready_wall_ms"],
                               signed_difference_pct=100*(right["ready_wall_ms"]/left["ready_wall_ms"]-1)))
            median=statistics.median(r["signed_difference_pct"] for r in aa)
            calibration=dict(window=window,pairs=aa,median_signed_difference_pct=median,
                             acceptance_abs_median_pct=3.0,passed=abs(median)<=3.0)
            doc["calibration"].append(calibration)
            save(a.out/"paired-full-port-e2e.json",doc)
            emit("aa_calibration",**calibration)
            assert calibration["passed"],("A/A platform calibration failed",calibration)
        pairs=[]
        for index in range(a.pairs):
            case=matrix[index%len(matrix)]
            order=[a.baseline,"full_dynamic"] if (window+index)%2==0 else ["full_dynamic",a.baseline]
            rows={label:sample(label,case,window,index) for label in order}
            b,c=rows[a.baseline]["ready_wall_ms"],rows["full_dynamic"]["ready_wall_ms"]
            pair=dict(window=window,pair=index,case=case[0],baseline=a.baseline,baseline_ms=b,candidate_ms=c,
                      reduction_pct=100*(1-c/b),order=order,
                      candidate_action_sha256=rows["full_dynamic"]["action_sha256"],
                      baseline_action_sha256=rows[a.baseline]["action_sha256"])
            pairs.append(pair);doc["pairs"].append(pair)
            emit("full_port_pair",**pair)
            save(a.out/"paired-full-port-e2e.json",doc)
        doc["summary"][str(window)]=summarize(pairs)
        doc["summary"][str(window)]["by_case"]={case[0]:summarize([r for r in pairs if r["case"]==case[0]])
            for case in matrix if any(r["case"]==case[0] for r in pairs)}
        save(a.out/"paired-full-port-e2e.json",doc)
    doc["complete"]=True
    doc["gate_passed"]=True
    doc["all_pairs"]=summarize(doc["pairs"])
    doc["formal_pair_count_per_window"]=a.pairs
    save(a.out/"paired-full-port-e2e.json",doc)
finally:
    if control is not None:control.close()
    engine.close()
