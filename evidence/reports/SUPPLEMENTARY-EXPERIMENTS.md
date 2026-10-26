<!-- Archived report: paths and links adapted; see evidence/ORIGIN-MANIFEST.json. -->
# 动态路径续跑：完整模型消融与拒绝证据

V3主语言40对配对中位降幅29.1609308%，按总耗时降幅28.8252885%，没有稳定达到30%。本文件保留后续探索的完整拒绝证据；最终采用的V4组合与直接官方对照结论见完整报告。

所有实验保持BF16、4步、CFG3、不同正负文本、每请求冷UND、在线VAE到ready GPU action边界。完整请求均实际VAE1、engine_step1、condition_encode2、denoiser8。准备或复制发生在计时区间内。

## 按运行时间排序的实验

| UTC开始 → 结束 | 实验 / 变量 | 实际完整请求 | 配对数 | 配对中位改善 | 总耗时改善 | 结论 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 2026-10-23T21:25:57.965159+00:00 → 2026-10-23T21:28:04.295059+00:00 | sampler-residency-screen-v1-attempt2<br>sigma | 16 | 4 | 0.053298% | -0.538865% | 未过1%门槛，拒绝晋升 |
| 2026-10-23T21:25:57.965159+00:00 → 2026-10-23T21:28:04.295059+00:00 | sampler-residency-screen-v1-attempt2<br>sigma_constants | 16 | 0 | 未计时 | 未计时 | 实际常数复用门槛失败；不使用性能 |
| 2026-10-23T21:30:22.199811+00:00 → 2026-10-23T21:34:33.676788+00:00 | request-residency-screen-v4-window0<br>sigma_constants | 36 | 4 | 0.019758% | 1.208654% | 未过1%门槛，拒绝晋升 |
| 2026-10-23T21:30:22.199811+00:00 → 2026-10-23T21:34:33.676788+00:00 | request-residency-screen-v4-window0<br>key_ahead | 36 | 4 | 1.305913% | 1.606117% | 只通过首窗，独立复验未过，拒绝晋升 |
| 2026-10-23T21:30:22.199811+00:00 → 2026-10-23T21:34:33.676788+00:00 | request-residency-screen-v4-window0<br>sigma_constants_key_ahead | 36 | 4 | -0.182999% | -1.111758% | 未过1%门槛，拒绝晋升 |
| 2026-10-23T21:35:07.300652+00:00 → 2026-10-23T21:38:05.411931+00:00 | request-coefficients-screen-v1-window0<br>coefficients | 24 | 4 | -0.296917% | 0.614700% | 未过1%门槛，拒绝晋升 |
| 2026-10-23T21:35:07.300652+00:00 → 2026-10-23T21:38:05.411931+00:00 | request-coefficients-screen-v1-window0<br>coefficients_key_ahead | 24 | 4 | 0.693739% | -0.580657% | 未过1%门槛，拒绝晋升 |
| 2026-10-23T21:40:20.832027+00:00 → 2026-10-23T21:43:01.111904+00:00 | key-ahead-independent-window1<br>key_ahead | 20 | 8 | -0.036729% | 0.037468% | 只通过首窗，独立复验未过，拒绝晋升 |

统计中的正数表示比相邻V3完整请求快，负数表示慢。各运行的完整请求数包含warmup，同一运行多变体共享该总数。进入复验需所有byte/物理dispatch门槛通过，且配对中位与总耗时改善均≥1%。没有因接近门槛改变阈值，也没有把弱收益相加成新候选。

## 精度与运行时证据

所有这些运行的完整模型BF16 action均与独立原官方archive逐storage byte相等，所有物理GEN计数均1152 GEMM/288 attention。系数预计算另有48项逐步随机velocity序列与原UniPC byte对照，覆盖1/2/4/5/8步、linear/Karras和两种张量rank；这些数值通过没有被当作性能通过。

## 关键修复和拒绝

1. 首次远程入口误传bench/前缀，run_with_binary_manifest_v8.py:6在加载模型之前拒绝；用新tag改为文件名重试，保留原失败run。
2. constants v1将cuda与cuda:0直接比较，20次tensor构造均未命中代理；BF16正确但actual-dispatch门槛失败。v2正规化device index后，14次one复用、6次half复用门槛通过，完整模型仍没有稳定性能收益。
3. 未执行的cold-key bypass源码被主动拒绝：不填condition_cache会改变后续请求缓存收益。实际测试改为保留原内容key/LRU/active branch语义，把4次token/mask host tuple复制移到请求开始。第二进程换token长度且BA/AB反转，未重现首窗收益。
4. 原GPU FP32 UniPC系数与linalg.solve仅提前至同请求set_timesteps，且只在本请求video/action两sampler间复用；所有sample相关BF16操作顺序保留。数值全过，性能未过，未叠加进最终入口。

## 相反权重布局筛选


| GEN类别 | 原布局row-major | 新布局row-major | 新Torch/原Lt单核耗时比 | 通过3类byte门槛后选中 |
| --- | --- | --- | ---: | --- |
| cross_attention_qkv_proj | False | True | 1.012551 | False |
| cross_attention_to_out | False | True | 0.879585 | True |
| mlp_gate_up_proj | False | True | 1.337349 | False |
| mlp_down_proj | True | False | 1.152158 | False |

只有attention output投影的新row-major权重布局和torch.mm进入完整模型筛选；单核约12.04%改善不作为E2E结论。36层重新pack多占1,207,959,552 bytes（1.125GiB），只作用于M3542；其他M保持原动态fallback。对应captures保留Thor的results/opposite-layout-main-screen-v1/captures，选择清单和源/二进制hash已取回。

## 可复查入口

- [原V3正式报告](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/reports/DYNAMIC-FULL-PORT-V3.md) · [最终V4报告](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/reports/DYNAMIC-FULL-PORT.md)
- [当前原始Workflow Trace](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/workflow-trace.jsonl)
- 每组results/<tag>/independent-screen-audit.json保存无Torch独立复算；原始sampler-residency-e2e.json、run.json、环境与source/binary清单并存。

Trace ID: wf-20261023T191907391908Z-63abb6795e。

原始续跑阶段快照生成UTC：2026-10-23T21:48:10.839917+00:00

## V4最终采用的布局组合：完整模型双进程筛选

| UTC开始 → 结束 | 独立运行 / 变体 | 完整请求 | 配对数 | 相对V3配对中位改善 | 总计时改善 | 门槛 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 2026-10-23T21:47:27.166784+00:00 → 2026-10-23T21:50:23.206081+00:00 | opposite-layout-e2e-screen-v1-window0<br>selected_all | 24 | 4 | -4.070494% | -3.550703% | 完整E2E退化，拒绝 |
| 2026-10-23T21:47:27.166784+00:00 → 2026-10-23T21:50:23.206081+00:00 | opposite-layout-e2e-screen-v1-window0<br>selected_out_torch_down | 24 | 4 | 8.222650% | 8.656161% | 通过初筛；仅组合被最终V4采用 |
| 2026-10-23T21:52:09.699813+00:00 → 2026-10-23T21:54:45.635154+00:00 | opposite-layout-e2e-confirm-v2-window1<br>selected_out_torch_down | 20 | 8 | 7.027465% | 6.774878% | 通过初筛；仅组合被最终V4采用 |

44次完整请求包括不计时warmup。上表收益相对V3，只用于选择；最终对官方的百分比由新的四个独立正式窗口直接计算，不使用乘法外推。单核筛选、新布局单项失败和组合成功全部保留。

V4完整质量25/25及额外4/4独立raw BF16 storage门槛通过。same-CFG原CSE执行器的extension dispatch为0；不同CFG和两个新stream为576。首次额外测试误预期288已在新harness修复，候选字节未变；原失败目录也一并发布。

完整append-only Trace及最终finish状态见[WORKFLOW-TRACE](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/reports/WORKFLOW-TRACE.md)。
