"""Runtime Q/K lengths, bounded stream-local plans, conservative ABI fallback."""
from collections import OrderedDict, Counter
from dataclasses import dataclass
import torch
import flashinfer
from phyai.layers.attention.enums import AttnLayout, AttnMode
from compact_attention_route_v13 import extension

@dataclass
class Plan:
    wrapper: object
    workspace: torch.Tensor
    qo: torch.Tensor
    kv: torch.Tensor
    done: object
    stream: int

class CompactAttention:
    max_plans = 4
    workspace_bytes = 128 * 1024 * 1024

    def __init__(self, transformer):
        self.bindings = []
        self.layers = []
        self.official_forwards = []
        self.plans = OrderedDict()
        self.calls = 0
        self.stats = Counter()
        for layer in transformer.gen_layers:
            mod = layer.cross_attention.attn
            old = mod.forward
            index = len(self.layers)
            self.layers.append(mod)
            self.official_forwards.append(old)
            def forward(q, k, v, attention_context=None, _old=old, _index=index):
                reason = self.unsupported(q, k, v, attention_context, _index)
                if reason is not None:
                    self.stats["fallback:" + reason] += 1
                    return self.official_forwards[_index](q, k, v, attention_context)
                qs, ks, vs = q.squeeze(0), k.squeeze(0), v.squeeze(0)
                stream = torch.cuda.current_stream(q.device)
                key = (tuple(qs.shape), tuple(ks.shape), tuple(vs.shape),
                       tuple(qs.stride()), tuple(ks.stride()), tuple(vs.stride()),
                       qs.dtype, ks.dtype, vs.dtype, qs.device, stream.cuda_stream)
                plan = self.plans.get(key)
                if plan is None:
                    self.stats["plan_misses"] += 1
                    workspace = torch.empty(self.workspace_bytes, device=q.device, dtype=torch.uint8)
                    wrapper = flashinfer.BatchPrefillWithRaggedKVCacheWrapper(
                        workspace, kv_layout="NHD", backend="cutlass")
                    qo = torch.tensor([0, qs.shape[0]], device=q.device, dtype=torch.int32)
                    kv = torch.tensor([0, ks.shape[0]], device=q.device, dtype=torch.int32)
                    wrapper.plan(qo, kv, qs.shape[1], ks.shape[1], qs.shape[2],
                                 causal=False, sm_scale=self.layers[_index].scale,
                                 q_data_type=qs.dtype, kv_data_type=ks.dtype)
                    plan = Plan(wrapper, workspace, qo, kv, torch.cuda.Event(), stream.cuda_stream)
                    self.plans[key] = plan
                    if len(self.plans) > self.max_plans:
                        _, retired = self.plans.popitem(last=False)
                        retired.done.synchronize()
                        self.stats["evictions"] += 1
                else:
                    self.stats["plan_hits"] += 1
                    self.plans.move_to_end(key)
                ve = torch.ones((*vs.shape[:-1], 192), device=v.device, dtype=v.dtype)
                ve[..., :128].copy_(vs)
                out = torch.empty((*qs.shape[:-1], 128), device=q.device, dtype=q.dtype)
                extension().run(plan.workspace, qs, ks, ve, plan.qo, plan.kv,
                                *plan.wrapper._plan_info, out, None, 0,
                                self.layers[_index].scale, 1., 1., 1., 1., qs.shape[0])
                plan.done.record(stream)
                self.calls += 1
                return out.unsqueeze(0)
            self.bindings.append((mod, old, forward))

    def unsupported(self, q, k, v, context=None, index=0):
        tensors = (q, k, v)
        if not all(isinstance(x, torch.Tensor) and x.ndim == 4 for x in tensors):
            return "rank"
        if not all(x.is_cuda and x.dtype == torch.bfloat16 for x in tensors):
            return "device_or_dtype"
        if q.device != k.device or q.device != v.device:
            return "device"
        if q.shape[0] != 1 or k.shape[0] != 1 or v.shape[0] != 1:
            return "batch"
        if q.shape[-2:] != (32,128) or k.shape[-2:] != (8,128) or v.shape != k.shape:
            return "geometry"
        if min(q.shape[1], k.shape[1]) <= 0:
            return "empty"
        if any(x.stride(-1) != 1 or any(a <= 0 for a in x.stride()) or x.data_ptr() % 16 for x in tensors):
            return "layout"
        if torch.cuda.is_current_stream_capturing():
            return "capture"
        mod = self.layers[index]
        if mod.causal or mod.sliding_window is not None or mod.logits_soft_cap is not None or mod.scale != 128 ** -.5:
            return "attention_semantics"
        if context is not None and (context.mask is not None or context.layout != AttnLayout.PADDED_4D or
                                    context.mode == AttnMode.IDLE or context.cu_seqlens_q is not None or
                                    context.cu_seqlens_kv is not None):
            return "attention_context"
        return None

    def supports(self, q, k, v, context=None, index=0):
        return self.unsupported(q, k, v, context, index) is None

    def enable(self):
        for mod, old, forward in self.bindings:
            mod.forward = forward

    def restore(self):
        for mod, old, forward in self.bindings:
            mod.forward = old

    def clear(self):
        for plan in self.plans.values():
            plan.done.synchronize()
        self.plans.clear()
