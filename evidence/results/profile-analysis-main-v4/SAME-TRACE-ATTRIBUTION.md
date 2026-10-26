# Dynamic request: physical kernel attribution

CUDA kernel correlation -> CUDA runtime/driver event -> same-thread explicit CPU scope

| Quantity | Observed |
| --- | ---: |
| GEN GEMM scopes / CUDA kernels | 1152 / 1152 |
| GEN attention scopes / v40 main kernels | 288 / 288 |
| All CUDA kernels inside GEN attention scopes | 870 |
| All kernel launches | 7869 |
| Summed kernel duration | 4960.330 ms |
| Kernel busy interval union | 4953.626 ms |
| GPU activity busy interval union | 4955.656 ms |
| GEN GEMM duration sum | 3121.553 ms |
| GEN attention duration sum | 879.998 ms |

kernel duration sum, busy union, and unprofiled ready-wall E2E are different quantities; no causal speedup or MFU inferred

the v40 Sm100Fmha kernel is attention; generic tool's memory label is heuristic

| GPU stage | Kernels | Sum (ms) |
| --- | ---: | ---: |
| cosmos3_stage/VAE_encode | 286 | 53.489 |
| cosmos3_stage/engine_step | 8 | 0.029 |
| cosmos3_stage/UND_encode | 1996 | 130.076 |
| unattributed | 693 | 2.108 |
| cosmos3_stage/GEN_forward | 4886 | 4774.628 |

No overlap or fusion savings are established by this candidate-only trace. Full workflow three-table output is preserved separately.
