"""All accepted dynamic optimizations plus validated per-M Lt fallback."""
from pathlib import Path
import importlib.util
from dynamic_lt_fallback_v1 import DynamicLtFallback
_spec = importlib.util.spec_from_file_location("cosmos_full_port_parent", Path(__file__).with_name("candidate-dynamic-v4.py"))
parent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parent)

class Control(parent.Control):
    def __init__(self, transformer, vae, engine):
        super().__init__(transformer, vae, engine)
        self.dynamic_lt = DynamicLtFallback(self.frozen.base.linear)

    def full(self, *args, **kwargs):
        before = self.dynamic_lt.stats.copy()
        try:
            return super().full(*args, **kwargs)
        finally:
            self.last_request_stats["dynamic_lt_extension"] = {
                "counters": dict(self.dynamic_lt.stats - before),
                "accepted_M": sorted(map(int, self.dynamic_lt.selected)),
                "unchanged_original_M": 3542,
                "unknown_shape_fallback": "inherited dynamic torch.mm",
                "same_cfg_pair_local_reuse_preserved": True,
                "no_cross_request_values": True,
            }

    def close(self):
        self.dynamic_lt.close()
        super().close()

def install(transformer, vae, engine):
    return Control(transformer, vae, engine)
