"""Screen actual GEN inputs for dynamic-M Lt; no model/E2E claims from these timings."""
from dynamic_model_common_full_v3 import *
import ctypes
import gc
import statistics

a = parser().parse_args()
engine, vae, vae_runner, counts = setup(a)
task = Path(os.environ["COSMOS_TASK_ROOT"])
spec = importlib.util.spec_from_file_location("cosmos_lt_screen_parent", task / "solution/candidate-dynamic-v4.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
control = None
doc = dict(complete=False, actual_model_inputs=True, screen_only=True, shapes=[])
selected = dict(status="screen_selected_requires_full_model_gate", configurations={})
save(a.out / "main-lt-screen.json", doc)
try:
    control = module.install(engine.entry.transformer, vae, engine)
    linear = control.frozen.base.linear
    lib = linear.lib
    P, I, S = ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t
    for name, args, ret in [
        ("lt_count", [P], I), ("lt_attr_full", [P, I, I], I),
        ("lt_ws", [P, I], S), ("lt_error", [P], I)]:
        fn = getattr(lib, name); fn.argtypes = args; fn.restype = ret
    stream = torch.cuda.current_stream().cuda_stream
    workspace = torch.empty(64 * 1024 * 1024, dtype=torch.uint8, device="cuda")
    by_module = {id(mod): fast.__defaults__ for mod, frozen, fast in linear.bindings}
    first = {id(m): name.split(".", 2)[2].replace(".", "_") for name, m in engine.entry.transformer.named_modules()
             if name.startswith("gen_layers.0.") and id(m) in by_module}
    def timed(fn, iterations=1):
        begin, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        begin.record()
        for _ in range(iterations): fn()
        end.record(); end.synchronize()
        return begin.elapsed_time(end) / iterations
    for case_name, pixels, request, use_stream, metadata in cases(a):
        assert not use_stream
        captured = {}
        hooks = []
        for mod, _, fast in linear.bindings:
            if id(mod) not in first: continue
            category = first[id(mod)]
            def capture(mod, args, result, _category=category):
                if _category not in captured:
                    captured[_category] = (args[0].detach().clone().reshape(-1, args[0].shape[-1]),
                                           result[0].detach().clone().reshape(-1, result[0].shape[-1]),
                                           by_module[id(mod)][1], by_module[id(mod)][3])
            hooks.append(mod.register_forward_hook(capture))
        try:
            engine.entry.scheduler.runner.reset()
            engine.entry.scheduler.runner._condition_cache.clear()
            output, model_row = measured(lambda: control.full(pixels, request, vae_runner, engine), counts, request)
            reference = torch.load(a.reference / "actions" / (case_name + ".pt"), map_location="cuda", weights_only=True)
            assert torch.equal(output.contiguous().view(torch.uint8), reference.contiguous().view(torch.uint8))
        finally:
            for hook in hooks: hook.remove()
        for category, (x, reference, weight, inherited_attrs) in captured.items():
            idle()
            m, k = x.shape; n = weight.shape[1]
            row = dict(case=case_name, category=category, shape=[m, n, k], b_row=bool(weight.stride(-1)==1),
                       input_sha256=action_hash(x), reference_sha256=action_hash(reference),
                       inherited_attrs=inherited_attrs, candidates=[])
            doc["shapes"].append(row)
            capture_dir = a.out / "captures"; capture_dir.mkdir(exist_ok=True)
            torch.save(dict(x=x.cpu(), reference=reference.cpu()), capture_dir / (str(m) + "-" + category + ".pt"))
            plan = lib.lt_make(m, n, k, int(weight.stride(-1)==1), workspace.numel(), 64)
            try:
                row["plan_status"] = lib.lt_error(plan)
                inherited = (I * 9)(*[inherited_attrs[str(i)] for i in range(9)])
                row["inherited_index"] = lib.lt_configure(plan, inherited, workspace.numel())
                assert m == 3542 and row["inherited_index"] >= 0
                row["inherited_median_ms"] = None
                out = torch.empty_like(reference)
                def run(index, value=x, destination=out):
                    rc = lib.lt_run(plan, index, value.data_ptr(), weight.data_ptr(), destination.data_ptr(),
                                    workspace.data_ptr(), workspace.numel(), stream)
                    assert rc == 0, (category, m, index, rc)
                for _ in range(3): torch.mm(x, weight, out=out)
                row["torch_mm_median_ms"] = statistics.median(timed(lambda: torch.mm(x, weight, out=out), 3) for _ in range(7))
                assert torch.equal(out.view(torch.uint8), reference.view(torch.uint8)), ("captured reference differs from torch.mm", category, m)
                run(row["inherited_index"])
                row["inherited_times_ms"] = [timed(lambda:run(row["inherited_index"]),3) for _ in range(7)]
                row["inherited_median_ms"] = statistics.median(row["inherited_times_ms"])
                coarse = []
                for index in range(lib.lt_count(plan)):
                    try:
                        coarse.append((timed(lambda: run(index)), index))
                    except RuntimeError as error:
                        row["candidates"].append(dict(index=index, error=str(error)))
                shortlist = sorted(coarse)[:16]
                if row["inherited_index"] >= 0 and not any(i == row["inherited_index"] for _, i in shortlist):
                    shortlist.append((0, row["inherited_index"]))
                generator = torch.Generator(device="cuda").manual_seed(314159 + m)
                changed = torch.randn(x.shape, dtype=x.dtype, device=x.device, generator=generator)
                fixtures = [("actual", x, reference), ("changed", changed, torch.mm(changed, weight)),
                            ("zero", torch.zeros_like(x), torch.zeros_like(reference))]
                for _, index in shortlist:
                    entry = dict(index=index, attrs={str(j): lib.lt_attr_full(plan,index,j) for j in range(9)}, byte_checks={})
                    row["candidates"].append(entry)
                    for label, value, ref in fixtures:
                        out.fill_(float("nan")); run(index, value, out); torch.cuda.synchronize()
                        entry["byte_checks"][label] = bool(torch.equal(out.view(torch.uint8), ref.view(torch.uint8)))
                        if not entry["byte_checks"][label]: break
                    entry["all_bytes_equal"] = len(entry["byte_checks"]) == len(fixtures) and all(entry["byte_checks"].values())
                    if entry["all_bytes_equal"]:
                        entry["times_ms"] = [timed(lambda: run(index), 3) for _ in range(7)]
                        entry["median_ms"] = statistics.median(entry["times_ms"])
                        entry["ratio_to_torch_mm"] = entry["median_ms"] / row["torch_mm_median_ms"]
                        entry["ratio_to_inherited_lt"] = entry["median_ms"] / row["inherited_median_ms"]
                    save(a.out / "main-lt-screen.json", doc)
                exact = [v for v in row["candidates"] if v.get("all_bytes_equal") and v.get("ratio_to_inherited_lt", 1) < 0.97]
                row["selected"] = min(exact, key=lambda v:v["median_ms"]) if exact else None
                if row["selected"] is not None:
                    selected["configurations"].setdefault(str(m), {})[category] = dict(
                        shape=[m,n,k],b_row=bool(weight.stride(-1)==1),attrs=row["selected"]["attrs"],
                        actual_and_changed_input_byte_gate=True,method="lt", screen_ratio_to_inherited=row["selected"]["ratio_to_inherited_lt"],
                        evidence=str((a.out / "main-lt-screen.json").relative_to(task)))
                emit("dynamic_lt_shape", case=case_name, category=category, shape=row["shape"],
                     torch_mm_ms=row["torch_mm_median_ms"], selected=row["selected"])
                save(a.out / "main-lt-screen.json", doc)
                save(a.out / "main-lt-screen-selected-v1.json", selected)
            finally:
                lib.lt_free(plan)
            del x, reference, weight
            gc.collect()
        captured.clear()
        gc.collect()
    doc["complete"] = True
    save(a.out / "main-lt-screen.json", doc)
    save(a.out / "main-lt-screen-selected-v1.json", selected)
finally:
    if control is not None: control.close()
    engine.close()
