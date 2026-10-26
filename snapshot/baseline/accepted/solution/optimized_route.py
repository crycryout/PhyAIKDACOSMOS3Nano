"""Exact BF16 Cosmos3 Nano pixels-to-action route for the frozen Thor workload."""
from pathlib import Path
import importlib.util
import os
import torch

class OptimizedPolicy:
    def __init__(self, engine, vae, vae_runner):
        task = Path(__file__).resolve().parents[1]
        configured = os.environ.setdefault("COSMOS_TASK_ROOT", str(task))
        if Path(configured).resolve() != task:
            raise ValueError("COSMOS_TASK_ROOT must identify this route's task directory")
        if engine.entry.scheduler.runner.use_cuda_graph:
            raise ValueError("This route requires the validated CUDA Graph OFF configuration")
        if torch.cuda.get_device_capability() != (11, 0):
            raise ValueError("This compiled route targets Thor SM110")
        path = task / "solution/candidate-v11.py"
        spec = importlib.util.spec_from_file_location("cosmos3_exact_bf16_route", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.engine, self.vae_runner = engine, vae_runner
        self.control = module.install(engine.entry.transformer, vae, engine)
        self.control.set_mode("combined_packed_exact")
        self.closed = False

    @torch.no_grad()
    def __call__(self, pixels, request):
        if self.closed:
            raise RuntimeError("This policy route is closed")
        if tuple(pixels.shape) != (1, 3, 33, 480, 832):
            raise ValueError("Validated pixels shape is [1,3,33,480,832]")
        if pixels.dtype != torch.bfloat16 or not pixels.is_cuda:
            raise ValueError("Validated pixels dtype/device is CUDA BF16")
        return self.control.full(pixels, request, self.vae_runner, self.engine)

    def close(self):
        if not self.closed:
            self.control.close()
            self.closed = True

def create_optimized_policy(engine, vae, vae_runner):
    return OptimizedPolicy(engine, vae, vae_runner)
