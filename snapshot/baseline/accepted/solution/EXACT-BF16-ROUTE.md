# Cosmos3 Nano exact BF16 route

The entry is solution/optimized_route.py. It runs the frozen official PhyAI
75403624f9c8858f347f624e3b032553fa756ac2 model through the task-owned candidate-v11
adapter and the attention-v12 CUDA implementation.

Use the Thor environment and PYTHONPATH from bench/run_experiment_v4.sh, then:

    from optimized_route import create_optimized_policy
    fast_policy = create_optimized_policy(engine, vae, vae_runner)
    action = fast_policy(pixels, request)
    fast_policy.close()

The timed call includes online VAE encoding of the consumed causal conditioning
prefix, the complete original diffusion loop, attention V packing and output
materialization. Keep B1, BF16 pixels [1,3,33,480,832], text96, diffusion4, CFG3,
seed42 and CUDA Graph OFF. Model loading, offline packed-weight preparation and
JIT compilation are warmup/setup. The 36 packed down-projection weights retain
BF16 and add about 3.375 GiB of storage.

The adapter combines the original exact GEN preparation, BF16-rounded residual
RMS fusion, direct BF16 GEMMs with packed down-projection weights, and KV64
attention whose BF16 denominator is accumulated through a constant-one PV
channel. The FP32 accumulator is normalized before the BF16 output cast.

Kernel and model accuracy evidence is in results/resume7-denominator-input-guards-v1,
results/resume7-denominator-eight-case-v1 and
results/resume7-denominator-model-byte-audit.json. All seven attention and eight
full-model cases are byte-identical to their official references, including the
nondefault stream. Graph replay is outside the fixed Graph OFF workload.

Formal acceptance requires two independent windows of 20 valid interleaved
pairs, 5 A/A pairs per window (<=2% median drift), above-L2 bandwidth drift <=3%,
matched sampled GPU/EMC frequencies and no foreign GPU work. Symmetric cooldown
and active compute/memory warmup are outside every inference timing region.
The final report supplies the actual formal outcome; screening numbers are
not the acceptance result.

The source patch applies at the task directory root. The source manifest hashes
every runtime source and benchmark harness. The original baseline snapshot is
retained in baseline/phyai-official.
