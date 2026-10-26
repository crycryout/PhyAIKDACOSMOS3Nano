<!-- Archived report: paths and links adapted; see evidence/ORIGIN-MANIFEST.json. -->
# COSMOS3 Nano BF16：静态优化完整迁移至动态路径

最终入口为 solution/candidate-full-port-v3.py。相对新进程中的原始 PhyAI 官方路径，主动态语言工作负载的两窗口配对中位 E2E 分别降低 30.0689% 和 28.7774%。共 82 对正式配对、196 个计时输出，每个输出均通过独立官方 BF16 原始字节门槛。

本轮迁移已完成验证；主动态路径各窗口是否达到30%：False。历史三轮静态百分比不作为本轮的实测分母。

## 1. 主动态语言路径：直接对官方测量

四组不同的正/负 CFG 文本按请求切换：len31_17、len65_97、len128_129、len257_7。默认视频33×480×832、action32，GEN M=3542。每个窗口是独立加载模型的进程，含20对AB/BA。

| 独立窗口 | 配对数 | 官方中位 ms | 最终版中位 ms | 配对降幅中位数 | 总计时降幅 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 20 | 8586.585 | 6027.499 | 30.0689% | 29.3766% |
| 1 | 20 | 8676.980 | 6198.706 | 28.7774% | 28.2821% |

40对合并的配对降幅中位数为 29.1609%；按总耗时计算为 28.8253%。合并只用于这四组均衡的主语言测试，不混入下面更小视频等不同workload。

| 主语言案例 | 配对数 | 官方中位 ms | 最终版中位 ms | 配对降幅中位数 |
| --- | ---: | ---: | ---: | ---: |
| len128_129 | 10 | 8624.287 | 6148.500 | 28.8900% |
| len257_7 | 10 | 8692.130 | 6148.654 | 28.9876% |
| len31_17 | 10 | 8632.968 | 6081.883 | 30.2981% |
| len65_97 | 10 | 8549.736 | 6126.657 | 29.2147% |

公式：对每个相邻pair计算100×(1−candidate_ms/official_ms)，再取中位数。比中位耗时之比、总耗时之比分别保存；未删除慢样本。

## 2. 视频和action变化：分层结果

| 案例 | GEN M | 配对数 | 官方中位 ms | 最终版中位 ms | 配对降幅中位数 | 两窗各自降幅 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| action16 | 3526 | 14 | 8689.846 | 5893.400 | 32.5052% | 35.3807% / 32.3605% |
| video17frames | 1982 | 14 | 4210.577 | 2990.721 | 29.4108% | 29.4571% / 29.3645% |
| video320x512 | 1472 | 14 | 3295.261 | 2290.163 | 29.7497% | 29.9051% / 29.5944% |

上述数值是各形状相对原始官方的完整E2E，不能与主语言负载混成生产流量加权收益。M=3542/1472等是视频patch加action的query数，语言长度影响UND及KV，两者不混淆。

## 3. 三轮优化逐项如何进入动态路径

| 历史优化 | 最终动态处理 | 实际证据 / 边界 |
| --- | --- | --- |
| 因果VAE条件前缀 | 按每请求cond_frame_indexes计算消费前缀，在线运行VAE | 25模型case含条件帧0/2；相同计时边界 |
| GEN准备融合 | 保留官方BF16 precision casts，运行时Q/K等信息 | 继承Graph-off preparation；Graph走官方回退 |
| residual add + RMS | 保留BF16中间舍入及原累加语义 | 不限定M3542；完整action逐字节一致 |
| 144个GEN GEMM / packed weights | 运行时M；保留原M3542 Lt配置；其他M原动态torch.mm | 不把固定算法无guard推广 |
| R2 Lt新形状 | 新增M1472四类GEMM；按shape/N/K/stride/device/stream保护 | 其他M回退；manifest固定，1152次真实dispatch |
| 精确compact attention v40 | 按Q/K/V真实shape建plan；LRU4、tail和stream保护 | 12尾块、8淘汰、4种原官方fallback、3新stream |
| R2 GEMM/attention CSE | 动态输入仍保留等价证明；仅相同CFG输入允许复用 | 相同CFG物理GEMM576 / attention144 |
| R3 RMS/SiLU/preparation CSE | 相同CFG保留；不同CFG执行完整两支 | 不同CFG物理GEMM1152 / attention288；无跨请求输出复用 |
| R3 native proof / route signatures | 在CSE有效路径保留完整guard | disabled wrapper零计数不冒称实际算子为零 |

相同长度不等于相同CFG内容：新案例same_length_different_cfg为47/47但内容不同，实际仍1152 GEMM和288 attention。未知M816通过原动态GEMM计算并与独立官方字节一致。Batch2、Graph等未证明优化适用的请求通过保存的真正原始官方方法回退。

## 4. 本轮选择、拒绝与回退

V1先在实际GEN输入上筛选三个M×四类GEMM，要求实际输入、换值和零输入逐字节一致，并有孤立kernel速度收益。9组过初筛后，完整模型双窗发现M1982整组慢约9.7%、M3526整组慢约5%–7%，因此拒绝整组推广。V1原始数据与源码保留。

随后拆5个类别做完整模型消融，50次请求均字节一致。M1982 QKV初看约1.75%收益，V2复验两窗只有1.4019% / 0.0350%，第二窗未过1%性能门槛，最终V3移除。M3526各新增配置均未过门槛，继续原torch.mm。M1472四类组合在V2确认中为10.6261% / 8.8311%的额外E2E降幅；其配置和计算在最终V3中保持。该父动态对照为筛选证据，每窗每case4对，不与正式官方对照的20/21对混用。

孤立kernel快不足以证明模型快。保留原动态fallback也是迁移的一部分：算法特化只在有可靠完整模型收益的形状启用。被拒绝的R3-v10 sigma实验、未实际采用的Lt v4和历史失败候选都不作为本轮已采用优化。

## 5. 精度与计时公平性

独立官方在未安装候选的新进程生成22份oracle，其中前20份又与旧官方archive逐storage byte核对一致。最终V3完整25/25通过；独立审核用zipfile只读取唯一raw BF16 storage，不导入Torch或执行pickle。语言1至512、padding/有效prefix、换token、换mask、换pixels、返回旧长度、视频/动作变化、非默认stream、LRU淘汰及未知M均覆盖。

正式每行都包含VAE1、engine_step1、condition_encode2、denoiser8；相同输入/seed/checkpoint/BF16/steps4/CFG3/flow_shift5/Karras=False/Graph=False。每次清UND与condition cache，两模式每个case均先两次完整不计时warmup。A/A每窗4对，abs median signed drift≤3%；AB/BA随pair交替，第二进程反转起始顺序。未改时钟、电源、driver或其他任务。实际身份、每秒遥测、source/binary manifests和所有计时行保存。

| 正式运行 | 模型PID | A/A中位有符号差 | 配对数 | 外来GPU干扰 |
| --- | ---: | ---: | ---: | --- |
| formal-main-v3-window0 | 1759912 | -0.1602% | 20 | False |
| formal-main-v3-window1 | 1761640 | -0.1628% | 20 | False |
| formal-shapes-v3-window0 | 1763398 | -0.6296% | 21 | False |
| formal-shapes-v3-window1 | 1764628 | 0.3453% | 21 | False |

时间从GPU pixels到ready GPU BF16 action，包含在线VAE、原engine.step、UND、8次GEN和action head。排除模型加载、tokenization、CPU图像预处理、可选视频decode和机器人后处理；两边一致。案例是确定性变化token IDs与pixels，不是自然语言任务或机器人rollout成功率评估。没有把本轮计时条件或数字冒充原静态三轮的同一workload。

## 6. Graph兼容与同一trace物理归因

Graph测试先在未安装候选时用真正官方Graph跑11/7与33/19，再安装最终版走官方回退；两长度action均字节一致，cond/uncond有真实capture/replay。这里只证明兼容回退，没有候选Graph加速数字。

Profiler先两次len31_17完整warmup，再profile一次video320x512完整请求，输出对独立官方字节一致。实际运行Workflow PhyAI三表分析器；根据CUDA correlation→runtime/driver→同线程显式CPU scope做归因。Profiler耗时不用于上面的speedup。

| 同一候选trace量 | 实测 |
| --- | ---: |
| GEN GEMM主kernel | 1152 |
| GEN attention v40主kernel | 288 |
| 全kernel launch | 7865 |
| GEN GEMM kernel sum | 1403.126 ms |
| GEN attention scope全部kernel sum | 180.660 ms |
| 全kernel duration sum | 2026.369 ms |
| kernel busy interval union | 2020.676 ms |

kernel sum、busy union、GPU activity union、同步E2E含义不同，不相减冒称可省时间。v40 FMHA kernel按源码归attention；通用工具的memory标签只是heuristic。未声明未知硬件peak对应的MFU，也未凭候选单trace编造因果分项收益。

## 7. Agent如何使用Workflow

1. start记录任务/目的/目标，read --show读取工作流合同、原官方动态实现、历史R1/R2/R3及具体行段/hash；保持当前任务独立目录。
2. 审核真实继承调用链，先独立官方oracle，再实际GEN输入的kernel筛选和完整模型数值门槛。每条有界命令用run --purpose记录argv/cwd/退出码/日志。
3. 用event记录V1整组回退、类别消融、V2弱收益拒绝及最终V3选择，失败不清理，不根据文件名推断成功。
4. 先完整动态byte门槛，再四个独立进程的未profile相邻E2E；另抓候选native trace核实真实完整计算。标准库审核独立复算输出、AB/BA、phase counts与统计。
5. 登记源码、补丁、二进制清单、正式计时、Graph、trace和报告；如实finish。完成Trace生成逐事件时间线和读取快照，再在独立交付流程发布。

本轮没有派子Agent；本轮read是root实际工具事件。历史多Agent读取记录保留在前轮独立chronology目录，并通过本轮read明确引用。Trace记录可观察执行和显式目的，不声称记录隐藏思考或证明阅读理解。

## 8. 复现与证据入口

使用solution/candidate-full-port-v3.py及完整继承solution/baseline目录；设置COSMOS_TASK_ROOT，加入solution到PYTHONPATH，调用install(engine.entry.transformer,vae,engine)，每请求调用control.full(pixels,request,vae_runner,engine)，结束close。动态请求并发须使用独立runner；本轮未验证运行时权重替换，更换权重应重建control。invalidate_cache用于清理现有runner及plan状态。

bench/run_dynamic_v3.sh包含本Thor ARM64 Python和checkpoint部署路径。换机器需明确修改部署路径并在目标设备重验；本机H800只做源码和CPU分析。实际formal argv在各run.json和Trace，不把筛选命令当正式命令。

| 内容 | 路径 |
| --- | --- |
| 结构化最终结果 | [final-outcome-v3.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/final-outcome-v3.json) |
| 完整独立存储/计时审核 | [final-independent-audit-v3.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/final-independent-audit-v3.json) |
| 独立进程/源码/二进制审核 | [release-runtime-audit-v3.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/release-runtime-audit-v3.json) |
| 最终候选精度 | [validation.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-gate-v3/validation.json) |
| 新官方oracle | [validation.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/official-fresh-v1/validation.json) |
| 所有选择与拒绝 | [逐事件时间线](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/reports/WORKFLOW-CHRONOLOGY.md) |
| Agent具体读取记录 | [READ-PROVENANCE.md](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/reports/READ-PROVENANCE.md) |
| Workflow工具Markdown | [WORKFLOW-TRACE.md](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/reports/WORKFLOW-TRACE.md) |
| 原始JSONL | [workflow-trace.jsonl](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/workflow-trace.jsonl) |
| 同trace归因 | [SAME-TRACE-ATTRIBUTION.md](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/profile-analysis-v3/SAME-TRACE-ATTRIBUTION.md) |

Trace ID: wf-20261023T191907391908Z-63abb6795e。
