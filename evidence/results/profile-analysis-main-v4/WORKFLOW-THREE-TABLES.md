Triage View
Mode: single-trace
Framework: PhyAI (Thor offline trace)
Input traces: $TASK_ROOT/results/profile-main-full-port-v4/candidate-dynamic.trace.json

Kernel Table
| Kernel | Category | GPU time | Share | Launches | Python location (site share) | CPU op |
| --- | --- | ---: | ---: | ---: | --- | --- |
| nvjet_sm110_tst_256x256_64x4_2x2_2cta_h_bz_TNT | gemm | 1475.72 ms | 29.7% | 288 | cublaslt_route_v2.py:33 fast | cuLaunchKernelEx |
| nvjet_sm110_tst_256x240_64x4_2x1_2cta_v_bz_NNT | gemm | 1291.23 ms | 26.0% | 576 | opposite_layout_routes_v1.py:21 route | aten::mm |
| void cutlass::device_kernel<cutlass::fmha::kernel::Sm100FmhaFwdKernelTmaWarpspecialized<cute::tuple<cutlass::fmha::collective::VariableLength, cutlass::fmha::collective::VariableLength, int, cute::tuple<cute::tuple<int, int>, int> >, cutlass::fmha::collective::Sm100FmhaFwdMainloopTmaWarpspecializedPV144V40<cutlass::bfloat16_t, float, float, cute::tuple<cute::C<256>, cute::C<64>, cute::C<128> >, cute::tuple<cute::C<256>, cute::C<192>, cute::C<64> >, cute::tuple<int, cute::C<1>, cute::tuple<int, int> >, cute::tuple<int, cute::C<1>, cute::tuple<cute::C<0>, int> >, cute::tuple<cute::C<1>, int, cute::tuple<cute::C<0>, int> >, cutlass::fmha::collective::ResidualMask, cute::tuple<cute::C<2>, cute::C<1>, cute::C<1> > >, cutlass::fmha::collective::Sm100FmhaFwdEpilogueTmaWarpspecialized<cutlass::bfloat16_t, float, cute::tuple<cute::C<128>, cute::C<128>, cute::C<64> > >, cutlass::fmha::kernel::HostPrecomputedTileScheduler, cutlass::fmha::kernel::Sm100FmhaCtxKernelWarpspecializedSchedule> > | memory | 846.76 ms | 17.1% | 288 | compact_attention_dynamic_v2.py:35 forward | cudaLaunchKernelExC |
| nvjet_sm110_tst_256x224_64x3_1x2_v_bz_TNT | gemm | 354.60 ms | 7.1% | 288 | cublaslt_route_v2.py:33 fast | cuLaunchKernelEx |
| void flashinfer::activation::act_and_mul_kernel<__nv_bfloat16, &(silu(float const&))> | activation | 310.03 ms | 6.2% | 360 | flashinfer/activation.py:48 _act_and_mul | cudaLaunchKernelExC |
| kernel_cutlass_kernel_rounded_add_rmsnorm_v1RoundedAddRMSNormKernel_object_at__tensorptrbf16gmemalign128oi64409640961_tensorptrbf16gmemalign16o40961_tensorptrbf16gmemalign128oi64409640961_0 | norm | 246.59 ms | 5.0% | 568 | rounded_add_rmsnorm_v1.py:446 rounded_add_rmsnorm | cudaLaunchKernelExC |
| kernel_cutlass_kernel_flashinfernormkernelsrmsnormQKRMSNormKernel_object_at__tensorptrbf16gmemalign16oi64i64128i64div8i64div81_tensorptrbf16gmemalign16o1281_tensorptrbf16gmemalign16oi64i6_0 | norm | 88.40 ms | 1.8% | 576 | flashinfer/norm/kernels/rmsnorm.py:1326 qk_rmsnorm_cute | cudaLaunchKernelExC |
| triton_poi_fused_add_cat_mul_neg_slice_0 | other | 70.20 ms | 1.4% | 288 | home/tomorin/rjc/cosmos3-nano-bf16-dynamic-full-port-20261024/cache/torchinductor/gl/cgluy6zxqijb4nvtdgloqysml52jndd7vplur4noyvho2o3trkdk.py:319 call | triton_poi_fused_add_cat_mul_neg_slice_0 |

Overlap Opportunity Table
| Priority | Verdict | Kernel | Python scope | Formal signal | Dep risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| - | - | No rows cleared the 1.0% reporting bar. Use mapping/formal mode for overlap attribution. | - | - | - | - |

Fuse Opportunity Table
| Pattern | Confidence | Related GPU time | Share | Evidence kernels | Current kernel Python location | Candidate fused Python path | Rationale |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| No medium-confidence source-backed fusion opportunity matched this trace. | - | - | - | - | - | - | - |
