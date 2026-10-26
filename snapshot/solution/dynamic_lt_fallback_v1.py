"""Extend accepted Lt v2 through its existing fallback, with a frozen per-M manifest."""
from pathlib import Path
import collections
import ctypes
import json
import os
import torch

class DynamicLtFallback:
    def __init__(self, linear):
        self.linear = linear
        self.bindings = []
        self.stats = collections.Counter()
        doc = json.loads((Path(os.environ["COSMOS_TASK_ROOT"]) / "solution/dynamic-lt-selected-v1.json").read_text())
        self.selected = doc["configurations"]
        for module, frozen, fast in linear.bindings:
            defaults = fast.__defaults__
            assert len(defaults) == 4, ("Expected accepted Lt-v2 ABI", len(defaults))
            old, weight, category, attrs = defaults
            assert old is frozen
            def fallback(x, _old=old, _b=weight, _category=category):
                if not x.is_cuda or x.dtype != torch.bfloat16 or x.ndim < 2 or x.shape[-1] != _b.shape[0]:
                    self.stats["unsupported_input"] += 1
                    return _old(x)
                aa = x.reshape(-1, x.shape[-1])
                spec = self.selected.get(str(aa.shape[0]), {}).get(_category)
                if spec is None or aa.stride(-1) != 1 or aa.stride(0) != aa.shape[1]:
                    self.stats["frozen_fallback"] += 1
                    return _old(x)
                if list(spec["shape"]) != [aa.shape[0], _b.shape[1], aa.shape[1]] or bool(spec["b_row"]) != bool(_b.stride(-1) == 1):
                    self.stats["manifest_guard_fallback"] += 1
                    return _old(x)
                stream = torch.cuda.current_stream(aa.device).cuda_stream
                key = (tuple(aa.shape), tuple(_b.shape), tuple(_b.stride()), aa.device.index, stream, _category)
                if key not in linear.plans:
                    wskey = (aa.device.index, stream)
                    if wskey not in linear.workspaces:
                        linear.workspaces[wskey] = torch.empty(64 * 1024 * 1024, device=aa.device, dtype=torch.uint8)
                    workspace = linear.workspaces[wskey]
                    plan = linear.lib.lt_make(aa.shape[0], _b.shape[1], aa.shape[1],
                                              int(_b.stride(-1) == 1), workspace.numel(), 1)
                    values = (ctypes.c_int * 9)(*[spec["attrs"][str(i)] for i in range(9)])
                    index = linear.lib.lt_configure(plan, values, workspace.numel())
                    if index < 0:
                        linear.lib.lt_free(plan)
                        self.stats["configuration_fallback"] += 1
                        return _old(x)
                    linear.plans[key] = (plan, index, workspace)
                    self.stats["plan_miss"] += 1
                plan, index, workspace = linear.plans[key]
                output = torch.empty((aa.shape[0], _b.shape[1]), device=aa.device, dtype=aa.dtype)
                status = linear.lib.lt_run(plan, index, aa.data_ptr(), _b.data_ptr(), output.data_ptr(),
                                           workspace.data_ptr(), workspace.numel(), stream)
                if status != 0:
                    raise RuntimeError(("Dynamic Lt dispatch failed", _category, tuple(aa.shape), status))
                self.stats["dispatch"] += 1
                self.stats["M=" + str(aa.shape[0]) + "/" + _category] += 1
                # The accepted parent fallback increments its own linear.calls.
                return output.reshape(*x.shape[:-1], _b.shape[1]), None
            fast.__defaults__ = (fallback, *defaults[1:])
            self.bindings.append((fast, defaults, fast.__defaults__))

    def set_enabled(self, enabled):
        for fast, original, extended in self.bindings:
            fast.__defaults__ = extended if enabled else original

    def close(self):
        self.set_enabled(False)
        self.bindings.clear()
