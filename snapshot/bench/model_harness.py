"""Profile unmodified PhyAI Cosmos3 DROID BF16 operators on one Thor GPU."""
from __future__ import annotations

import argparse
import collections
import dataclasses
import functools
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

import torch

p = argparse.ArgumentParser()
p.add_argument('--checkpoint', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--mode', choices=['smoke', 'timing', 'profile'], default='smoke')
p.add_argument('--candidate', default='official')
p.add_argument('--pairs', type=int, default=20)
p.add_argument('--samples', type=int, default=7)
p.add_argument('--profile-samples', type=int, default=3)
p.add_argument('--height', type=int, default=480)
p.add_argument('--width', type=int, default=832)
p.add_argument('--frames', type=int, default=33)
p.add_argument('--text-tokens', type=int, default=96)
p.add_argument('--steps', type=int, default=4)
a = p.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
(a.out / 'target_pid.json').write_text(json.dumps(dict(pid=os.getpid(), start_ns=time.time_ns()))+'\n')
torch.set_grad_enabled(False)

def save(name, obj):
    (a.out / name).write_text(json.dumps(obj, indent=2, default=str) + '\n')

def emit(kind, **values):
    row = dict(kind=kind, time_ns=time.time_ns(), **values)
    with (a.out / 'events.jsonl').open('a') as f:
        f.write(json.dumps(row, default=str) + '\n')
    print(kind, json.dumps(values, default=str), flush=True)

def idle():
    raw = subprocess.check_output(['/usr/sbin/nvidia-smi', '--query-compute-apps=pid,process_name', '--format=csv,noheader'], text=True)
    others = [line for line in raw.splitlines() if line.strip() and int(line.split(',')[0]) != os.getpid()]
    if others:
        raise RuntimeError('Another compute process is present; refusing benchmark: ' + str(others))
    return raw

def sensors():
    values = {}
    for root, glob in [('/sys/class/devfreq', '*/cur_freq'), ('/sys/class/thermal', 'thermal_zone*/temp')]:
        for path in Path(root).glob(glob):
            try:
                values[str(path)] = int(path.read_text().strip())
            except (OSError, ValueError):
                pass
    return values

idle()
import phyai
import flashinfer
import phyai_kernel.jit_utils.compile as jit_compile
jit_compile.PHYAI_KERNEL_CACHE_ROOT = Path(os.environ['COSMOS_TASK_ROOT']) / 'cache/phyai_kernel'
from phyai import Engine, EngineArgs
from phyai.engine_config import DeviceConfig, EngineConfig, RuntimeConfig
from phyai.models.cosmos3.main_cosmos3_policy import Cosmos3PolicyArgs
from phyai.models.cosmos3 import Cosmos3ActionRequest, Cosmos3WanVAE, Cosmos3WanVAEConfig, cosmos3_vae_weight_remap, pixel_to_latent_shape
from phyai.models.cosmos3.model_runner_vae_cosmos3 import Cosmos3VAERunner
from phyai.models.cosmos3.modeling_cosmos3 import DomainAwareLinear
from phyai.layers.linear.layers import LinearBase
from phyai.utils import load_config
from phyai.weights import load_pretrained

emit('LOAD_START', checkpoint=str(a.checkpoint), mode=a.mode)
engine = Engine(EngineArgs(
    plugin='cosmos3_policy',
    plugin_args=Cosmos3PolicyArgs(checkpoint_dir=a.checkpoint, flow_shift=5.0, use_karras_sigmas=False, decode_video=False),
    config=EngineConfig(device=DeviceConfig(target='cuda', params_dtype=torch.bfloat16), runtime=RuntimeConfig(use_cuda_graph=False)),
))
transformer = engine.entry.transformer
vae = Cosmos3WanVAE(load_config(a.checkpoint / 'vae', Cosmos3WanVAEConfig))
load_pretrained(vae, a.checkpoint / 'vae', remap=cosmos3_vae_weight_remap, strict=False)
vae = vae.to(device='cuda', dtype=torch.bfloat16).eval()
vae_runner = Cosmos3VAERunner(vae, device='cuda', dtype=torch.bfloat16)
vae_runner.setup()

# Match the repository benchmark's fixed synthetic observation/token fixture.
# Preserve the real checkpoint, model dimensions, DROID domain and complete loop.
gen = torch.Generator(device='cuda').manual_seed(42)
pixels = torch.rand(1, 3, a.frames, a.height, a.width, device='cuda', dtype=torch.bfloat16, generator=gen) * 2 - 1
text_ids = torch.full((1, a.text_tokens), 100, dtype=torch.long, device='cuda')
text_mask = torch.ones_like(text_ids)
video_shape = pixel_to_latent_shape(a.frames, a.height, a.width)
request = Cosmos3ActionRequest(text_ids=text_ids, text_mask=text_mask, neg_text_ids=text_ids, neg_text_mask=text_mask,
    video_shape=video_shape, mode='policy', domain_id=8, action_chunk=32, raw_action_dim=10, action_dim=64,
    fps=15.0, num_inference_steps=a.steps, guidance_scale=3.0, seed=42, cond_frame_indexes=(0,))

manifest = []
for name, mod in transformer.named_modules():
    if isinstance(mod, LinearBase):
        manifest.append(dict(name=name, cls=type(mod).__name__, spec=mod.spec.spec_id,
            weight_shape=list(mod.weight.shape), weight_dtype=str(mod.weight.dtype)))
    elif isinstance(mod, DomainAwareLinear):
        manifest.append(dict(name=name, cls=type(mod).__name__, implementation='torch.bmm', parameters={n:dict(shape=list(v.shape), dtype=str(v.dtype)) for n,v in mod.named_parameters()}))
save('linear_manifest.json', manifest)
save('environment.json', dict(torch=torch.__version__, flashinfer=flashinfer.__version__, phyai_source=phyai.__file__,
    gpu=torch.cuda.get_device_name(), capability=torch.cuda.get_device_capability(), pid=os.getpid(),
    source_commit=(Path(os.environ['COSMOS_SOURCE_ROOT'])/'REVISION').read_text().strip(),
    runtime_cuda_graph=engine.entry.scheduler.runner.use_cuda_graph,
    tensor_dtypes=dict(collections.Counter(str(t.dtype) for t in transformer.parameters())),
    vae_dtypes=dict(collections.Counter(str(t.dtype) for t in vae.parameters())), sensors=sensors()))
save('workload.json', dict(model='Cosmos3-Nano-Policy-DROID', batch=1, dtype='BF16', frames=a.frames,
    height=a.height, width=a.width, video_latent_shape=video_shape, text_tokens=a.text_tokens,
    action_chunk=32, raw_action_dim=10, action_dim=64, steps=a.steps, guidance_scale=3., cfg_branches=2,
    flow_shift=5., use_karras_sigmas=False, fps=15., seed=42, input_kind='fixed synthetic benchmark fixture',
    full_boundary='GPU observation pixels -> VAE encode -> original engine.step -> GPU action output',
    core_boundary='precomputed observation latent -> original engine.step -> GPU action output',
    excluded=['model load','tokenization','image preprocessing','optional video decode','action postprocess','robot communication'],
    original_example_decode_video=False, operator_replacements=False))

profile_active = False
phase_counts = collections.Counter()
def phase_wrap(obj, name, label):
    original = getattr(obj, name)
    @functools.wraps(original)
    def wrapped(*args, **kwargs):
        phase_counts[label] += 1
        if profile_active:
            torch.cuda.nvtx.range_push('cosmos_stage:' + label)
        try:
            return original(*args, **kwargs)
        finally:
            if profile_active:
                torch.cuda.nvtx.range_pop()
    setattr(obj, name, wrapped)

phase_wrap(vae_runner, 'encode', 'vae_encode')
phase_wrap(transformer, 'encode_condition', 'condition_encode')
phase_wrap(transformer, 'forward', 'denoiser')
phase_wrap(engine, 'step', 'engine_step')

def full():
    latent = vae_runner.encode(pixels)
    return engine.step(dataclasses.replace(request, cond_video_latents=latent))

emit('LOAD_DONE', memory_allocated_gib=torch.cuda.memory_allocated()/2**30, video_shape=video_shape)
torch.cuda.synchronize()
cached_latent = vae_runner.encode(pixels)
core_request = dataclasses.replace(request, cond_video_latents=cached_latent)
def core():
    return engine.step(core_request)

reference = {}
def measure(fn, label):
    idle()
    torch.cuda.synchronize()
    before_sensors = sensors()
    phase_counts.clear()
    if profile_active:
        torch.cuda.nvtx.range_push('cosmos_e2e:' + label)
    start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    start.record()
    t0 = time.perf_counter()
    output = fn()
    submitted = time.perf_counter()
    end.record()
    end.synchronize()
    ready = time.perf_counter()
    if profile_active:
        torch.cuda.nvtx.range_pop()
    row = dict(label=label, event_ms=start.elapsed_time(end), ready_wall_ms=(ready-t0)*1000,
        host_submit_ms=(submitted-t0)*1000, phase_counts=dict(phase_counts), sensors_before=before_sensors, sensors_after=sensors())
    assert 0 <= row['phase_counts'].get('condition_encode', 0) <= 2, row
    assert row['phase_counts']['denoiser'] == a.steps * 2, row
    assert torch.isfinite(output).all(), 'Non-finite model output'
    assert list(output.shape) == [1,32,10], output.shape
    row['output_shape'] = list(output.shape)
    row['output_dtype'] = str(output.dtype)
    if 'action' not in reference:
        reference['action'] = output.clone()
        torch.save(output.cpu(), a.out / 'reference_action.pt')
    row['output_equal'] = bool(torch.equal(output, reference['action']))
    assert row['output_equal'], ('Official repeated action changed', row)
    row['output_relative_l2'] = float((output.float()-reference['action'].float()).norm()/reference['action'].float().norm().clamp_min(1e-12))
    emit('MEASURE', **row)
    return row


# This is a task-owned harness; the baseline checkout is never patched.
if a.candidate != "official":
    import importlib.util
    spec = importlib.util.spec_from_file_location("cosmos_candidate", Path(os.environ["COSMOS_TASK_ROOT"])/"solution"/"candidate.py")
    candidate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(candidate)
    control = candidate.install(transformer, vae, engine)
else:
    control = None
samples = []
try:
    for i in range(3 if a.mode == "smoke" else 3):
        row = measure(full, "warmup_"+str(i))
        samples.append(row)
        save("smoke.json", samples)
    if a.mode == "profile":
        from torch.profiler import profile, ProfilerActivity, record_function
        profile_active = True
        with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA], record_shapes=True) as prof:
            with record_function("cosmos3/full_pixels_to_action/"+a.candidate):
                samples.append(measure(full,"profile_full_0"))
        profile_active = False
        prof.export_chrome_trace(str(a.out/"model.trace.json"))
        save("profile_timing.json", samples)
    elif a.mode == "timing":
        for i in range(a.samples):
            samples.append(measure(full,"full_"+str(i)))
            save("timing.json", samples)
    save("complete.json", {"status":"complete","mode":a.mode,"candidate":a.candidate,"samples":samples})
finally:
    if control is not None and hasattr(control,"close"):
        control.close()
    engine.close()
