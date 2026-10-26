"""Experimental V4: V3 plus the independently screened M3542 GEMM combination."""
from pathlib import Path
import importlib.util
import json
from opposite_layout_routes_v1 import OppositeLayoutRoutes
_spec=importlib.util.spec_from_file_location("cosmos_full_port_v4_parent",Path(__file__).with_name("candidate-full-port-v3.py"))
parent=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parent)

class Control(parent.Control):
    def __init__(self,transformer,vae,engine):
        self._main_enabled=True
        self.main_routes=None
        super().__init__(transformer,vae,engine)
        selected=json.loads(Path(__file__).with_name("main-layout-selected-v4.json").read_text())["configurations"]["3542"]
        self.main_routes=OppositeLayoutRoutes(self.frozen.base.linear,selected)
        self.main_routes.set_variant("selected_out_torch_down")
        self.set_mode("candidate")

    def set_main_enabled(self,enabled):
        self._main_enabled=bool(enabled)
        if self.main_routes is not None:
            self.main_routes.set_variant("selected_out_torch_down" if self._main_enabled and self.mode=="candidate" else "inherited")

    def set_mode(self,mode):
        super().set_mode(mode)
        if self.main_routes is not None:
            self.main_routes.set_variant("selected_out_torch_down" if self._main_enabled and mode=="candidate" else "inherited")

    def full(self,*args,**kwargs):
        before=self.main_routes.stats.copy()
        try:
            return super().full(*args,**kwargs)
        finally:
            self.last_request_stats["main_gemm_extension"]={
                "enabled":self._main_enabled,
                "counters":dict(self.main_routes.stats-before),
                "supported_M":3542,
                "categories":["cross_attention_to_out","mlp_down_proj"],
                "output_projection_weight_row_major":True,
                "down_projection_unchanged_packed_layout":True,
                "additional_pack_bytes":self.main_routes.packed_bytes,
                "additional_packed_weights":len(self.main_routes.packed),
                "all_other_shapes":"inherited V3 dynamic fallback",
                "no_cross_request_outputs":True,
            }

    def close(self):
        self._main_enabled=False
        if self.main_routes is not None:self.main_routes.close()
        super().close()

def install(transformer,vae,engine):
    return Control(transformer,vae,engine)
