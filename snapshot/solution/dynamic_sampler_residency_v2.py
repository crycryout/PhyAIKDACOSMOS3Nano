"""Request-local GPU residency; original UniPC arithmetic and casts are unchanged."""
import collections
import contextlib
import types
import torch

class TorchConstants:
    def __init__(self, device, dtype, counters):
        self.device = torch.device(device)
        if self.device.type == "cuda" and self.device.index is None:
            self.device = torch.device("cuda", torch.cuda.current_device())
        self.dtype = dtype
        self.counters = counters
        self.one = torch.tensor(1.0, device=device)
        self.half = torch.tensor([0.5], dtype=dtype, device=device)
        counters["constant_uploads"] += 2
    def __getattr__(self, name):
        return getattr(torch, name)
    def tensor(self, data, *args, **kwargs):
        device = kwargs.get("device")
        dtype = kwargs.get("dtype", torch.get_default_dtype())
        if not args and set(kwargs) <= {"device", "dtype"} and device is not None and torch.device(device) == self.device:
            if type(data) is float and data == 1.0 and dtype == self.one.dtype:
                self.counters["one_reuses"] += 1
                return self.one
            if type(data) is list and data == [0.5] and dtype == self.dtype:
                self.counters["half_reuses"] += 1
                return self.half
        self.counters["unintercepted_tensor"] += 1
        return torch.tensor(data, *args, **kwargs)

def clone_with_torch(fn, proxy):
    namespace = dict(fn.__globals__)
    namespace["torch"] = proxy
    copy = types.FunctionType(fn.__code__, namespace, fn.__name__, fn.__defaults__, fn.__closure__)
    copy.__kwdefaults__ = fn.__kwdefaults__
    return copy

class SamplerResidency:
    def __init__(self):
        from phyai.models.cosmos3 import scheduler_cosmos3_policy
        self.owner = scheduler_cosmos3_policy
        self.original = self.owner.UniPCMultistepSampler
        self.stats = collections.Counter()
        self.active = False

    @contextlib.contextmanager
    def request(self, variant, dtype):
        assert variant in {"inherited", "sigma", "sigma_constants"}
        assert not self.active
        self.stats.clear()
        self.stats["request_contexts"] = 1
        if variant == "inherited":
            yield
            return
        original, stats = self.original, self.stats
        class ResidentSampler(original):
            def set_timesteps(self, num_inference_steps, device=None):
                super().set_timesteps(num_inference_steps, device=device)
                assert self.sigmas.dtype == torch.float32 and self.sigmas.device.type == "cpu"
                self.sigmas = self.sigmas.to(device=device)
                stats["sigma_table_uploads"] += 1
                if variant == "sigma_constants":
                    self._constants = TorchConstants(device, dtype, stats)
                    self._p_update = types.MethodType(clone_with_torch(original._p_update, self._constants), self)
                    self._c_update = types.MethodType(clone_with_torch(original._c_update, self._constants), self)
            def step(self, model_output, timestep, sample):
                assert sample.dtype == dtype and sample.device == self.sigmas.device
                stats["solver_steps"] += 1
                return super().step(model_output, timestep, sample)
        assert self.owner.UniPCMultistepSampler is original
        self.active = True
        self.owner.UniPCMultistepSampler = ResidentSampler
        try:
            yield
        finally:
            self.owner.UniPCMultistepSampler = original
            self.active = False
