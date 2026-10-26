"""Encode the causal pixel prefix consumed by a Cosmos3 policy request."""
from __future__ import annotations
from typing import Any
import torch


def encode_conditioning_pixels(vae_runner: Any, pixels: torch.Tensor, request: Any) -> torch.Tensor:
    """Retain full public VAE semantics and prune only unused policy conditioning."""
    indexes = request.cond_frame_indexes
    if indexes is None:
        indexes = tuple(range(request.video_shape[0])) if request.mode == "inverse_dynamics" else (0,)
    # Preserve the original path for empty, negative, or unusual frame selections.
    if indexes and all(0 <= i < request.video_shape[0] for i in indexes):
        scale = int(vae_runner.vae.scale_factor_temporal)
        required = 1 + scale * max(indexes)
        if required < pixels.shape[2]:
            pixels = pixels[:, :, :required]
    return vae_runner.encode(pixels)
