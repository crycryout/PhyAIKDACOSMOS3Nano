"""Runtime shape checks shared by the dynamic route and source proof."""
import torch
from phyai.layers.attention.enums import AttnLayout, AttnMode

def require_condition(args, kwargs, transformer, not_proven):
    if len(args) != 3:
        raise not_proven("unsupported_transformer_call")
    hidden, timestep, condition = args
    if hidden.ndim != 5 or hidden.shape[0] != 1 or hidden.dtype != torch.bfloat16:
        raise not_proven("unsupported_model_shape")
    if tuple(hidden.shape[-3:]) != tuple(condition.video_shape):
        raise not_proven("inconsistent_video_shape")
    if condition.sound_len != 0 or len(condition.cached_kv) != len(transformer.gen_layers):
        raise not_proven("unsupported_model_shape")
    action = kwargs.get("action_latents")
    if condition.action_len != (0 if action is None else action.shape[1]):
        raise not_proven("inconsistent_action_length")
    p = transformer.latent_patch_size
    t, h, w = condition.video_shape
    expected = t * ((h+p-1)//p) * ((w+p-1)//p) + condition.action_len
    if len(condition.freqs_gen) != 2 or any(x.shape[:2] != (1, expected) for x in condition.freqs_gen):
        raise not_proven("inconsistent_query_length")
    lengths = set()
    for key, value in condition.cached_kv:
        if key.ndim != 4 or key.shape[0] != 1 or key.shape != value.shape:
            raise not_proven("unsupported_cached_kv")
        lengths.add(key.shape[1])
    if len(lengths) != 1:
        raise not_proven("inconsistent_cached_kv_length")
    for context in condition.attention_contexts or ():
        if context is not None and (context.mask is not None or context.layout != AttnLayout.PADDED_4D or context.mode != AttnMode.PREFILL):
            raise not_proven("custom_attention_context")
