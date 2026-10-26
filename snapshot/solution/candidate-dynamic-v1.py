"""Dynamic Cosmos3 BF16 entry; original PhyAI remains the fallback."""
from pathlib import Path
import contextlib
import dataclasses
import importlib.util
import torch

_spec = importlib.util.spec_from_file_location(
    "cosmos_dynamic_parent", Path(__file__).with_name("candidate-round3-v11.py"))
parent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(parent)

class Control(parent.Control):
    def __init__(self, transformer, vae, engine):
        self._dynamic_ready = False
        self._official_bindings = [(mod, "forward", mod.forward) for mod in transformer.modules()]
        self._official_bindings.extend((layer.mlp, "_act_and_mul", layer.mlp._act_and_mul)
                                       for layer in transformer.gen_layers)
        runner = engine.entry.scheduler.runner
        self._official_runner_forward = runner.forward
        self._official_prepare = runner._attention_fusion.prepare
        self._official_preparation = runner._attention_fusion.forward
        self._engine = engine
        self._in_full = False
        self._closed = False
        super().__init__(transformer, vae, engine)
        self._candidate_prepare = runner._attention_fusion.prepare
        originals = {id(mod): method for mod, name, method in self._official_bindings if name == "forward"}
        self.compact.official_forwards = [originals[id(mod)] for mod in self.compact.layers]
        self._dynamic_ready = True
        self.set_mode("candidate")

    @property
    def compact(self):
        return self.frozen.base.compact

    def set_mode(self, mode):
        if not self._dynamic_ready:
            return super().set_mode(mode)
        if mode not in ("official", "baseline", "candidate"):
            raise ValueError(mode)
        runner = self._engine.entry.scheduler.runner
        previous = self.mode
        super().set_mode("baseline" if mode == "official" else mode)
        if mode == "official":
            for mod, name, method in self._official_bindings:
                setattr(mod, name, method)
            runner.forward = self._official_runner_forward
            runner._attention_fusion.prepare = self._official_prepare
            runner._attention_fusion.forward = self._official_preparation
        else:
            self.transformer.forward = self.proof_forward
            runner._attention_fusion.prepare = self._candidate_prepare
        self.mode = mode
        # A captured official graph must never outlive a route switch.
        if previous != mode:
            runner.invalidate_cache()

    def _fallback_reason(self, pixels, request, runner):
        if runner.use_cuda_graph:
            return "official_cuda_graph"
        if pixels.ndim != 5 or pixels.shape[0] != 1:
            return "official_batch_or_rank"
        if not pixels.is_cuda or pixels.dtype != torch.bfloat16:
            return "official_dtype_or_device"
        if request.mode != "policy":
            return "official_nonpolicy"
        return None

    def full(self, pixels, request, vae_runner, engine):
        if self._closed:
            raise RuntimeError("Dynamic control is closed")
        if self._in_full:
            raise RuntimeError("Concurrent requests require independent PhyAI runners")
        self._in_full = True
        mode = self.mode
        before = self.compact.stats.copy()
        fallback = self._fallback_reason(pixels, request, engine.entry.scheduler.runner) if mode != "official" else None
        try:
            if mode == "official" or fallback is not None:
                if mode != "official":
                    self.set_mode("official")
                value = vae_runner.encode(pixels)
                output = engine.step(dataclasses.replace(request, cond_video_latents=value))
                self.last_request_stats = {"dynamic": {"route": "official", "reason": fallback or "requested"}}
                return output
            # Preserve Lt descriptors/workspaces for at most two streams.
            linear = self.frozen.base.linear
            current = (pixels.device.index, torch.cuda.current_stream(pixels.device).cuda_stream)
            if current not in linear.workspaces and len(linear.workspaces) >= 2:
                torch.cuda.synchronize(pixels.device)
                for plan, index, workspace in linear.plans.values():
                    linear.lib.lt_free(plan)
                linear.plans.clear()
                linear.workspaces.clear()
            return super().full(pixels, request, vae_runner, engine)
        finally:
            if fallback is not None:
                self.set_mode(mode)
            if mode != "official" and fallback is None:
                self.last_request_stats["dynamic"] = {
                    "route": "optimized_eager", "text_padded": int(request.text_ids.shape[1]),
                    "negative_padded": None if request.neg_text_ids is None else int(request.neg_text_ids.shape[1]),
                    "video_shape": list(request.video_shape), "action_chunk": request.action_chunk,
                    "plan_entries": len(self.compact.plans), "plan_limit": self.compact.max_plans,
                    "plan_stats": dict(self.compact.stats - before),
                    "lt_plan_entries": len(self.frozen.base.linear.plans),
                    "lt_workspace_entries": len(self.frozen.base.linear.workspaces),
                    "pair_state_cleared": not self.frozen.entries and not self.frozen.attention_entries and not self.pure_entries}
            self._in_full = False

    def invalidate_cache(self):
        self.frozen.clear()
        self.clear_pure()
        self.cond_proof = None
        self.proof_refs = []
        self.native_route_records = None
        self.compact.clear()
        self._engine.entry.scheduler.runner.invalidate_cache()

    def close(self):
        if self._closed:
            return
        self.compact.clear()
        super().close()
        for mod, name, method in self._official_bindings:
            setattr(mod, name, method)
        runner = self._engine.entry.scheduler.runner
        runner.forward = self._official_runner_forward
        runner._attention_fusion.prepare = self._official_prepare
        runner._attention_fusion.forward = self._official_preparation
        runner.invalidate_cache()
        self._closed = True

def install(transformer, vae, engine):
    return Control(transformer, vae, engine)
