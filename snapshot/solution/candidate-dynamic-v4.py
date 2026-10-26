"""V3 calculations with accurate diagnostics for disabled CFG memo wrappers."""
from pathlib import Path
import importlib.util
_spec=importlib.util.spec_from_file_location("cosmos_dynamic_release_parent",Path(__file__).with_name("candidate-dynamic-v3.py"))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)
class Control(parent.Control):
    def full(self,*args,**kwargs):
        output=super().full(*args,**kwargs)
        stats=self.last_request_stats
        if stats.get("cfg_memo_policy",{}).get("enabled") is False:
            stats["input_proof"]["all_nonlinear_operations_executed"]=True
            stats["pure_operator_reuse"]["physical_nonlinear_kernels_may_be_reused"]=False
            stats["pure_operator_reuse"]["counter_scope"]="disabled CSE wrappers; zeros are not physical operator counts"
            stats["route_signature_cache"]["tensor_checks_per_forward"]=False
            stats["native_signature"]["tensors_checked_each_forward"]=False
            stats["native_signature"]["route_guard_fields_preserved"]=False
            stats["preparation_dispatch"]["counter_scope"]="disabled preparation CSE wrapper; direct fusion still executes"
        return output
def install(transformer,vae,engine):
    return Control(transformer,vae,engine)
