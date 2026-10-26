"""Move the native condition content-key copies to this request's timed start."""
import collections
import contextlib
import types

class RequestConditionKeys:
    def __init__(self, runner):
        self.runner=runner
        self.original=runner.condition
        self.graph_type=self.original.__func__.__globals__["Cosmos3CudaGraphRunner"]
        self.stats=collections.Counter()
        self.active=False

    @contextlib.contextmanager
    def request(self, enabled, request):
        self.stats.clear()
        runner,stats=self.runner,self.stats
        if not enabled or runner.use_cuda_graph:
            if enabled:stats["official_fallback"]+=1
            yield
            return
        assert not self.active
        # Keep native .cpu().tolist() conversion and its exact values; only move it
        # ahead of VAE/GEN. Never reuse a token tuple across requests.
        host=[]
        for tensor in [request.text_ids,request.text_mask,request.neg_text_ids,request.neg_text_mask]:
            host.append((tensor,tuple(tensor.detach().cpu().reshape(-1).tolist())))
            stats["host_tuple_copies"]+=1
        def contents(tensor):
            for original,value in host:
                if tensor is original:
                    stats["host_tuple_uses"]+=1
                    return value
            stats["unmatched_tensor_fallback"]+=1
            return tuple(tensor.detach().cpu().reshape(-1).tolist())
        graph_type=self.graph_type
        def condition(instance,branch,text_ids,text_mask,video_shape,fps=None,
                      *,action_len=0,sound_len=0,sound_fps=None):
            spec=(video_shape,fps,action_len,sound_len,sound_fps,
                  graph_type.tensor_signature({"text_ids":text_ids,"text_mask":text_mask}))
            cond=instance._conditions.get(branch)
            if cond is None or instance._condition_specs.get(branch)!=spec:
                parameter=next(instance.transformer.parameters())
                key=(spec,parameter.dtype,parameter.device,repr(instance.transformer.config),
                     contents(text_ids),contents(text_mask))
                entry=instance._condition_cache.get(key)
                if entry is None:
                    cond=instance.transformer.encode_condition(text_ids,text_mask,video_shape,fps,
                        action_len=action_len,sound_len=sound_len,sound_fps=sound_fps)
                    instance._next_condition_revision+=1
                    revision=instance._next_condition_revision
                    instance._condition_cache[key]=(cond,revision)
                    if len(instance._condition_cache)>2:instance._condition_cache.popitem(last=False)
                    stats["cold_encodes"]+=1
                else:
                    cond,revision=entry
                    instance._condition_cache.move_to_end(key)
                    stats["native_cache_hits"]+=1
                instance._conditions[branch]=cond
                instance._condition_specs[branch]=spec
                instance._condition_revisions[branch]=revision
            else:
                stats["active_branch_hits"]+=1
            return cond
        runner.condition=types.MethodType(condition,runner)
        self.active=True
        try:
            yield
        finally:
            runner.condition=self.original
            self.active=False
            host.clear()
