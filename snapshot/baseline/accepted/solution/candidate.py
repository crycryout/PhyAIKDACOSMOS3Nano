"""Task-scoped Cosmos3 BF16 candidates; the official checkout stays intact."""
from __future__ import annotations
import dataclasses
from conditioning_cosmos3 import encode_conditioning_pixels


class Control:
    def __init__(self, transformer, vae, engine):
        self.mode = "official"
        self.provider = engine.entry.scheduler.runner._attention_fusion
        self.original_prepare = self.provider.prepare
        def prepare(*, device, use_cuda_graph):
            use_fusion = use_cuda_graph or self.mode in ("fusion", "combined")
            return self.original_prepare(device=device, use_cuda_graph=use_fusion)
        self.provider.prepare = prepare

    def set_mode(self, mode):
        if mode not in ("official", "fusion", "prefix", "combined"):
            raise ValueError(mode)
        self.mode = mode

    def full(self, pixels, request, vae_runner, engine):
        if self.mode in ("prefix", "combined"):
            latent = encode_conditioning_pixels(vae_runner, pixels, request)
        else:
            latent = vae_runner.encode(pixels)
        return engine.step(dataclasses.replace(request, cond_video_latents=latent))

    def close(self):
        self.provider.prepare = self.original_prepare


def install(transformer, vae, engine):
    return Control(transformer, vae, engine)
