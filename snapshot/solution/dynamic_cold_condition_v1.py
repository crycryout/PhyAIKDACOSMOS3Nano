"""Skip cross-request content-key copies only inside an explicitly cold request."""
import collections
import contextlib
import types

class ColdConditionKeys:
    def __init__(self, runner):
        self.runner = runner
        self.original = runner.condition
        self.graph_type = self.original.__func__.__globals__["Cosmos3CudaGraphRunner"]
        self.stats = collections.Counter()
        self.active = False

    @contextlib.contextmanager
    def request(self, enabled):
        self.stats.clear()
        runner, stats = self.runner, self.stats
        if not enabled:
            yield
            return
        if runner.use_cuda_graph or runner._condition_cache:
            stats["official_fallback"] += 1
            yield
            return
        assert not self.active
        graph_type = self.graph_type
        def condition(instance, branch, text_ids, text_mask, video_shape, fps=None,
                      *, action_len=0, sound_len=0, sound_fps=None):
            spec=(video_shape,fps,action_len,sound_len,sound_fps,
                  graph_type.tensor_signature({"text_ids":text_ids,"text_mask":text_mask}))
            cond=instance._conditions.get(branch)
            if cond is None or instance._condition_specs.get(branch)!=spec:
                cond=instance.transformer.encode_condition(text_ids,text_mask,video_shape,fps,
                         action_len=action_len,sound_len=sound_len,sound_fps=sound_fps)
                instance._next_condition_revision+=1
                instance._conditions[branch]=cond
                instance._condition_specs[branch]=spec
                instance._condition_revisions[branch]=instance._next_condition_revision
                stats["cold_encodes"]+=1
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
