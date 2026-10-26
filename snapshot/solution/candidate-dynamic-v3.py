"""Skip CFG operator memoization when text inputs are provably different.

Every transformer/layer/operator still computes. Equal CFG text retains the
audited pair-local R3 proof. Different text avoids retaining tens of GB of
intermediates and hundreds of unsuccessful GPU byte comparisons.
"""
from pathlib import Path
import importlib.util
import torch
_spec=importlib.util.spec_from_file_location("cosmos_dynamic_v3_parent",Path(__file__).with_name("candidate-dynamic-v2.py"))
parent=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(parent)

def equal_input(left,right):
    if left is right:return True
    if not isinstance(left,torch.Tensor) or not isinstance(right,torch.Tensor):return False
    if left.shape!=right.shape or left.dtype!=right.dtype or left.device!=right.device:return False
    return bool(torch.equal(left.contiguous().view(torch.uint8),right.contiguous().view(torch.uint8)))

class Control(parent.Control):
    def full(self,pixels,request,vae_runner,engine):
        if self.mode!="candidate" or self._fallback_reason(pixels,request,engine.entry.scheduler.runner) is not None:
            return super().full(pixels,request,vae_runner,engine)
        same=(equal_input(request.text_ids,request.neg_text_ids) and
              equal_input(request.text_mask,request.neg_text_mask))
        if same:
            output=super().full(pixels,request,vae_runner,engine)
            self.last_request_stats["cfg_memo_policy"]={"enabled":True,"identical_text_inputs":True}
            return output
        # Restore the original runner to execute both branches in full.
        # Keep the accepted Lt, compact attention, rounded RMS and VAE routes.
        self.frozen.set_mode("baseline")
        self.frozen.base.set_mode("candidate")
        self.transformer.forward=self.original_transformer
        self.prepare_provider.forward=self.original_preparation
        for mod,name,old,new in self.pure_bindings:setattr(mod,name,old)
        self.pure_namespace["rounded_add_rmsnorm"]=self.original_rounded
        before=self.compact.calls
        try:
            return super().full(pixels,request,vae_runner,engine)
        finally:
            stats=self.last_request_stats
            physical=self.compact.calls-before
            if "dynamic" in stats and stats["dynamic"]["route"]=="optimized_eager":
                stats.update(physical_gen_attention=physical,logical_gen_attention=physical,
                             reused_gen_attention=0,attention_misses=0,attention_tensor_byte_comparisons=0)
                stats["cfg_memo_policy"]={"enabled":False,"identical_text_inputs":False,
                    "reason":"different CFG text inputs: compute both branches; no speculative operator memo",
                    "full_branch_execution":True}
                stats["pure_operator_reuse"]["enabled"]=False
                stats["pure_operator_reuse"]["counters_cover_only_enabled_memo_wrappers"]=True
            self.set_mode("candidate")

def install(transformer,vae,engine):
    return Control(transformer,vae,engine)
