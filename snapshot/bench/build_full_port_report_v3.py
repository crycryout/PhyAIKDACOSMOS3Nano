"""Build the final Chinese report strictly from completed, independently audited evidence."""
from pathlib import Path
import argparse,hashlib,json,statistics
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
read=lambda rel:json.loads((t/rel).read_text())
audit=read("results/final-independent-audit-v4.json")
runtime=read("results/release-runtime-audit-v4.json")
gate=read("results/candidate-gate-v4/validation.json")
graph=read("results/graph-fallback-full-port-v4/graph-fallback-validation.json")
profile=read("results/profile-main-full-port-v4/profile-metadata.json")
mapping=read("results/profile-analysis-main-v4/same-trace-physical-attribution.json")
assert all(x["complete"] for x in (audit,runtime,gate,graph,profile,mapping))
assert audit["gate_passed"] and runtime["gate_passed"] and gate["exact_gate_passed"] and graph["gate_passed"] and profile["byte_equal"]
def summarize(rows):
    bs=[r["baseline_ms"] for r in rows];cs=[r["candidate_ms"] for r in rows]
    return dict(samples=len(rows),baseline_median_ms=statistics.median(bs),candidate_median_ms=statistics.median(cs),paired_median_reduction_pct=statistics.median(100*(1-c/b) for b,c in zip(bs,cs)),reduction_from_medians_pct=100*(1-statistics.median(cs)/statistics.median(bs)),reduction_from_total_time_pct=100*(1-sum(cs)/sum(bs)),minimum_pair_reduction_pct=min(100*(1-c/b) for b,c in zip(bs,cs)),maximum_pair_reduction_pct=max(100*(1-c/b) for b,c in zip(bs,cs)))
families={}
for family in ("main","shapes"):
    pairs=[];windows={}
    for w in (0,1):
        rel=f"results/formal-{family}-v4-window{w}/paired-full-port-e2e.json"
        d=read(rel);assert rel in audit["paired_audits"]
        pairs.extend(d["pairs"]);windows[str(w)]=summarize(d["pairs"])
    families[family]=dict(windows=windows,pooled=summarize(pairs),by_case={name:summarize([r for r in pairs if r["case"]==name]) for name in sorted({r["case"] for r in pairs})})
for family in families:
    families[family]["by_case_windows"]={str(w):audit["paired_audits"][f"results/formal-{family}-v4-window{w}/paired-full-port-e2e.json"]["windows"][str(w)]["by_case"] for w in (0,1)}
main=families["main"]
target=all(r["paired_median_reduction_pct"]>=30 and r["reduction_from_total_time_pct"]>=30 for r in main["windows"].values())
outcome=dict(complete=True,migration_validated=True,at_least_30pct_each_main_window=target,official_revision="75403624f9c8858f347f624e3b032553fa756ac2",candidate="solution/candidate-full-port-v4.py",candidate_sha256=hashlib.sha256((t/"solution/candidate-full-port-v4.py").read_bytes()).hexdigest(),trace_id="wf-20261023T191907391908Z-63abb6795e",main_and_shape_statistics=families,full_model_byte_cases=len(gate["cases"]),official_oracle_cases=24,independent_model_pids=runtime["independent_model_pids"],formal_pairs=runtime["formal_pairs_total"],timed_byte_checked_rows=runtime["timed_rows_total"],active_new_M=[1472,3542],additional_model_byte_cases=4,additional_weight_pack_bytes=1207959552,rejected_new_M=[1982,3526],boundary="GPU pixels to ready GPU BF16 action; online VAE and original engine.step included",synthetic_fixture_limitation=True,no_claim_of_69pct_dynamic_gain=True)
(t/"results/final-outcome-v4.json").write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+"\n")
md=["# COSMOS3 Nano BF16：静态优化完整迁移至动态路径","",f"最终入口为 solution/candidate-full-port-v4.py。相对新进程中的原始 PhyAI 官方路径，主动态语言40对合并配对中位 E2E 降低 {main['pooled']['paired_median_reduction_pct']:.4f}%（按总耗时为 {main['pooled']['reduction_from_total_time_pct']:.4f}%）；两个独立窗口分别降低 {main['windows']['0']['paired_median_reduction_pct']:.4f}% 和 {main['windows']['1']['paired_median_reduction_pct']:.4f}%。共 {runtime['formal_pairs_total']} 对正式配对、{runtime['timed_rows_total']} 个计时输出，每个输出均通过独立官方 BF16 原始字节门槛。","",f"本轮迁移已完成验证；主动态路径各窗口是否达到30%：{target}。历史三轮静态百分比不作为本轮的实测分母。","","## 1. 主动态语言路径：直接对官方测量","","四组不同的正/负 CFG 文本按请求切换：len31_17、len65_97、len128_129、len257_7。默认视频33×480×832、action32，GEN M=3542。每个窗口是独立加载模型的进程，含20对AB/BA。","","| 独立窗口 | 配对数 | 官方中位 ms | 最终版中位 ms | 配对降幅中位数 | 总计时降幅 |","| --- | ---: | ---: | ---: | ---: | ---: |"]
for w,r in main["windows"].items():md.append(f"| {w} | {r['samples']} | {r['baseline_median_ms']:.3f} | {r['candidate_median_ms']:.3f} | {r['paired_median_reduction_pct']:.4f}% | {r['reduction_from_total_time_pct']:.4f}% |")
md.extend(["",f"40对合并的配对降幅中位数为 {main['pooled']['paired_median_reduction_pct']:.4f}%；按总耗时计算为 {main['pooled']['reduction_from_total_time_pct']:.4f}%。合并只用于这四组均衡的主语言测试，不混入下面更小视频等不同workload。","","| 主语言案例 | 配对数 | 官方中位 ms | 最终版中位 ms | 配对降幅中位数 | 两窗各自降幅 |","| --- | ---: | ---: | ---: | ---: | --- |"])
for name,r in main["by_case"].items():
    ws=[main["by_case_windows"][str(w)][name]["paired_median_reduction_pct"] for w in (0,1)]
    md.append(f"| {name} | {r['samples']} | {r['baseline_median_ms']:.3f} | {r['candidate_median_ms']:.3f} | {r['paired_median_reduction_pct']:.4f}% | {ws[0]:.4f}% / {ws[1]:.4f}% |")
md.extend(["","公式：对每个相邻pair计算100×(1−candidate_ms/official_ms)，再取中位数。比中位耗时之比、总耗时之比分别保存；未删除慢样本。","","## 2. 视频和action变化：分层结果","","| 案例 | GEN M | 配对数 | 官方中位 ms | 最终版中位 ms | 配对降幅中位数 | 两窗各自降幅 |","| --- | ---: | ---: | ---: | ---: | ---: | --- |"])
for name,r in families["shapes"]["by_case"].items():
    m={"video320x512":1472,"video17frames":1982,"action16":3526}[name]
    ws=[families["shapes"]["by_case_windows"][str(w)][name]["paired_median_reduction_pct"] for w in (0,1)]
    md.append(f"| {name} | {m} | {r['samples']} | {r['baseline_median_ms']:.3f} | {r['candidate_median_ms']:.3f} | {r['paired_median_reduction_pct']:.4f}% | {ws[0]:.4f}% / {ws[1]:.4f}% |")
md.extend(["","上述数值是各形状相对原始官方的完整E2E，不能与主语言负载混成生产流量加权收益。M=3542/1472等是视频patch加action的query数，语言长度影响UND及KV，两者不混淆。","","## 3. 三轮优化逐项如何进入动态路径","","| 历史优化 | 最终动态处理 | 实际证据 / 边界 |","| --- | --- | --- |","| 因果VAE条件前缀 | 按每请求cond_frame_indexes计算消费前缀，在线运行VAE | 25模型case含条件帧0/2；相同计时边界 |","| GEN准备融合 | 保留官方BF16 precision casts，运行时Q/K等信息 | 继承Graph-off preparation；Graph走官方回退 |","| residual add + RMS | 保留BF16中间舍入及原累加语义 | 不限定M3542；完整action逐字节一致 |","| 144个GEN GEMM / packed weights | 运行时M；M3542保留QKV/up的Lt；out/down由V4实测组合替换；其他M继承动态torch.mm | 不把固定算法无guard推广 |","| R2 Lt新形状 | M1472四类GEMM保留V3；按shape/N/K/stride/device/stream保护 | 其他M回退；manifest固定，1152次真实dispatch |","| 精确compact attention v40 | 按Q/K/V真实shape建plan；LRU4、tail和stream保护 | 12尾块、8淘汰、4种原官方fallback、3新stream |","| R2 GEMM/attention CSE | 动态输入仍保留等价证明；仅相同CFG输入允许复用 | 相同CFG物理GEMM576 / attention144 |","| R3 RMS/SiLU/preparation CSE | 相同CFG保留；不同CFG执行完整两支 | 不同CFG物理GEMM1152 / attention288；无跨请求输出复用 |","| R3 native proof / route signatures | 在CSE有效路径保留完整guard | disabled wrapper零计数不冒称实际算子为零 |","","相同长度不等于相同CFG内容：新案例same_length_different_cfg为47/47但内容不同，实际仍1152 GEMM和288 attention。未知M816通过原动态GEMM计算并与独立官方字节一致。Batch2、Graph等未证明优化适用的请求通过保存的真正原始官方方法回退。","","## 4. 动态Lt迁移阶段的选择、拒绝与回退","","V1先在实际GEN输入上筛选三个M×四类GEMM，要求实际输入、换值和零输入逐字节一致，并有孤立kernel速度收益。9组过初筛后，完整模型双窗发现M1982整组慢约9.7%、M3526整组慢约5%–7%，因此拒绝整组推广。V1原始数据与源码保留。","","随后拆5个类别做完整模型消融，50次请求均字节一致。M1982 QKV初看约1.75%收益，V2复验两窗只有1.4019% / 0.0350%，第二窗未过1%性能门槛，V3即已移除，最终V4也未启用。M3526各新增配置均未过门槛，继续原torch.mm。M1472四类组合在V2确认中为10.6261% / 8.8311%的额外E2E降幅；其配置和计算在最终V4中保持。该父动态对照为筛选证据，每窗每case4对，不与正式官方对照的20/21对混用。","","孤立kernel快不足以证明模型快。保留原动态fallback也是迁移的一部分：算法特化只在有可靠完整模型收益的形状启用。被拒绝的R3-v10 sigma实验、未实际采用的Lt v4和历史失败候选都不作为本轮已采用优化。","","## 5. 精度与计时公平性","","独立官方在未安装候选的新进程生成22份oracle，其中前20份又与旧官方archive逐storage byte核对一致。最终V4完整25/25通过；独立审核用zipfile只读取唯一raw BF16 storage，不导入Torch或执行pickle。语言1至512、padding/有效prefix、换token、换mask、换pixels、返回旧长度、视频/动作变化、非默认stream、LRU淘汰及未知M均覆盖。","","正式每行都包含VAE1、engine_step1、condition_encode2、denoiser8；相同输入/seed/checkpoint/BF16/steps4/CFG3/flow_shift5/Karras=False/Graph=False。每次清UND与condition cache，两模式每个case均先两次完整不计时warmup。A/A每窗4对，abs median signed drift≤3%；AB/BA随pair交替，第二进程反转起始顺序。未改时钟、电源、driver或其他任务。实际身份、周期遥测、source/binary manifests和所有计时行保存。","","| 正式运行 | 模型PID | A/A中位有符号差 | 配对数 | 外来GPU干扰 |","| --- | ---: | ---: | ---: | --- |"])
for r in runtime["runs"]:md.append(f"| {r['tag']} | {r['pid']} | {r['aa_median_signed_difference_pct']:.4f}% | {r['pairs']} | {r['interference_observed']} |")
md.extend(["","时间从GPU pixels到ready GPU BF16 action，包含在线VAE、原engine.step、UND、8次GEN和action head。排除模型加载、tokenization、CPU图像预处理、可选视频decode和机器人后处理；两边一致。案例是确定性变化token IDs与pixels，不是自然语言任务或机器人rollout成功率评估。没有把本轮计时条件或数字冒充原静态三轮的同一workload。","","## 6. Graph兼容与同一trace物理归因","","Graph测试先在未安装候选时用真正官方Graph跑11/7与33/19，再安装最终版走官方回退；两长度action均字节一致，cond/uncond有真实capture/replay。这里只证明兼容回退，没有候选Graph加速数字。","","V4 Profiler先两次len31_17完整warmup，再profile一次len65_97完整请求，输出对独立官方字节一致。实际运行Workflow PhyAI三表分析器；根据CUDA correlation→runtime/driver→同线程显式CPU scope做归因。Profiler耗时不用于上面的speedup。","","| 同一候选trace量 | 实测 |","| --- | ---: |",f"| GEN GEMM主kernel | {mapping['attributed_launches']['gen_gemm']} |",f"| GEN attention v40主kernel | {mapping['v40_attention_main_kernel_launches']} |",f"| 全kernel launch | {mapping['kernel_launches']} |",f"| GEN GEMM kernel sum | {mapping['gen_gemm_sum_ms']:.3f} ms |",f"| GEN attention scope全部kernel sum | {mapping['gen_attention_sum_ms']:.3f} ms |",f"| 全kernel duration sum | {mapping['kernel_duration_sum_ms']:.3f} ms |",f"| kernel busy interval union | {mapping['kernel_busy_union_ms']:.3f} ms |","","kernel sum、busy union、GPU activity union、同步E2E含义不同，不相减冒称可省时间。v40 FMHA kernel按源码归attention；通用工具的memory标签只是heuristic。未声明未知硬件peak对应的MFU，也未凭候选单trace编造因果分项收益。","","## 7. Agent如何使用Workflow","","1. start记录任务/目的/目标，read --show读取工作流合同、原官方动态实现、历史R1/R2/R3及具体行段/hash；保持当前任务独立目录。","2. 审核真实继承调用链，先独立官方oracle，再实际GEN输入的kernel筛选和完整模型数值门槛。每条有界命令用run --purpose记录argv/cwd/退出码/日志。","3. 用event记录V1整组回退、类别消融、V2弱收益拒绝及V3回退及V4新布局组合选择，失败不清理，不根据文件名推断成功。","4. 先完整动态byte门槛，再四个独立进程的未profile相邻E2E；另抓候选native trace核实真实完整计算。标准库审核独立复算输出、AB/BA、phase counts与统计。","5. 登记源码、补丁、二进制清单、正式计时、Graph、trace和报告；如实finish。完成Trace生成逐事件时间线和读取快照，再在独立交付流程发布。","","本轮没有派子Agent；本轮read是root实际工具事件。历史多Agent读取记录保留在前轮独立chronology目录，并通过本轮read明确引用。Trace记录可观察执行和显式目的，不声称记录隐藏思考或证明阅读理解。","","## 8. 复现与证据入口","","使用solution/candidate-full-port-v4.py及完整继承solution/baseline目录；设置COSMOS_TASK_ROOT，加入solution到PYTHONPATH，调用install(engine.entry.transformer,vae,engine)，每请求调用control.full(pixels,request,vae_runner,engine)，结束close。动态请求并发须使用独立runner；本轮未验证运行时权重替换，更换权重应重建control。invalidate_cache用于清理现有runner及plan状态。","","bench/run_dynamic_v3.sh包含本Thor ARM64 Python和checkpoint部署路径。换机器需明确修改部署路径并在目标设备重验；本机H800只做源码和CPU分析。实际formal argv在各run.json和Trace，不把筛选命令当正式命令。","","| 内容 | 路径 |","| --- | --- |","| 结构化最终结果 | [final-outcome-v4.json](../results/final-outcome-v4.json) |","| 完整独立存储/计时审核 | [final-independent-audit-v4.json](../results/final-independent-audit-v4.json) |","| 独立进程/源码/二进制审核 | [release-runtime-audit-v4.json](../results/release-runtime-audit-v4.json) |","| 最终候选精度 | [validation.json](../results/candidate-gate-v4/validation.json) |","| 新官方oracle | [validation.json](../results/official-fresh-v1/validation.json) |","| 所有选择与拒绝 | [逐事件时间线](WORKFLOW-CHRONOLOGY.md) |","| Agent具体读取记录 | [READ-PROVENANCE.md](READ-PROVENANCE.md) |","| Workflow工具Markdown | [WORKFLOW-TRACE.md](WORKFLOW-TRACE.md) |","| 原始JSONL | [workflow-trace.jsonl](../results/workflow-trace.jsonl) |","| 同trace归因 | [SAME-TRACE-ATTRIBUTION.md](../results/profile-analysis-main-v4/SAME-TRACE-ATTRIBUTION.md) |","",f"Trace ID: {outcome['trace_id']}。",""])

route_audit=read("results/formal-route-audit-v4.json")
assert route_audit["complete"] and route_audit["gate_passed"]
under=[dict(window=w,case=name,paired_median_reduction_pct=r["paired_median_reduction_pct"]) for w,v in main["by_case_windows"].items() for name,r in v.items() if r["paired_median_reduction_pct"]<30]
outcome["individual_main_case_windows_below_30pct"]=under
if under:
    md.extend(["", "主窗口整体超过30%并不表示每条请求或每个长度单窗都超过30%。低于30%的单案例窗口："+ "；".join(f"window{r['window']} {r['case']} {r['paired_median_reduction_pct']:.4f}%" for r in under)+"。", ""])
md.extend(["", "本轮保持设备原有自然DVFS，未锁定或改变GPU/EMC频率；周期频率与外来进程检查随各run.json保留。配对顺序反转、独立进程及A/A用于控制测量漂移；结论限定于此合同，未外推其它时钟或流量分布。", ""])

extra_gate=read("results/extra-main-independent-audit-v4.json")
assert extra_gate["complete"] and extra_gate["gate_passed"]
v3=read("results/final-outcome-v3.json")
outcome["predecessor_v3_main_paired_median_pct"]=v3["main_and_shape_statistics"]["main"]["pooled"]["paired_median_reduction_pct"]
outcome["extra_main_validation_audit"]="results/extra-main-independent-audit-v4.json"
(t/"results/final-outcome-v4.json").write_text(json.dumps(outcome,ensure_ascii=False,indent=2)+"\n")
md.extend(["","## 9. V3未达标后，V4如何补上主动态路径收益","",
"V3已经完成可适用的历史迁移，主语言40对合并中位29.1609308%、总计时28.8252885%，两窗口30.0689% / 28.7774%，没有稳定达到30%。这些失败结果保留于[原V3报告](DYNAMIC-FULL-PORT-V3.md)，没有删窗、重选最快结果或与其它视频形状混算。","",
"V4仅新增M3542的两个真实GEN GEMM路由：cross_attention_to_out将原packed col-major权重重新pack为row-major后用torch.mm；mlp_down_proj仍用原packed布局，改为torch.mm。其余M和算子全部继承V3。新增36份权重pack共1,207,959,552 bytes（1.125 GiB），在初始化完成，权重值逐元素相同。E2E排除模型安装，两模式安装与warmup条件一致。该内存增加是实际代价，未评估并发容量。","",
"单独out新布局在完整E2E中反而慢4.0705%；out与down的组合才进入复验。第一进程len65_97四对相对V3中位8.22265%、总计时8.65616%；第二进程len128_129八对并反转BA/AB，中位7.02747%、总计时6.77488%。这些是筛选，不与官方百分比相乘；本报告的最终百分比直接来自四个正式官方对照进程。","",
"最终V4通过25项完整模型byte验证，以及4项额外M3542验证。额外验证包含same-CFG、同长度但不同CFG内容和新stream；两项新oracle由未安装候选的独立官方进程生成。same-CFG走父CSE：真实物理GEN GEMM576/attention144，新extension dispatch=0；不同CFG及新stream真实extension dispatch=576、UND2/GEN8。报告以实际计数判定路由，没有把enabled标志冒充实际执行。首次额外harness错误预期same-CFG的新dispatch=288导致失败；修复harness为0并验证父物理计数，候选字节未变，失败记录保留。","",
"系数预计算、sigma/constants复用、condition-key前移等续跑方案虽精度通过，但没有可复现的完整E2E收益，均未并入V4。[补充实验](SUPPLEMENTARY-EXPERIMENTS.md)保留原始结果与拒绝原因。","",
"![40对全部样本](figures/main-paired-latency-v4.png)","",
"## 10. 历史Agent读取记录与本轮的关系","",
"本轮未派子Agent，所有本轮读取均由root通过read --show记录。原多Agent历史按原证据身份保留：",
"[第一轮时间线](../../cosmos3-nano-bf16-workflow-chronology/CHRONOLOGY.md)、[第一轮读取来源](../../cosmos3-nano-bf16-workflow-chronology/READ-PROVENANCE.md)、[第二轮READ-EVENTS](../../cosmos3-nano-bf16-round2-30pct-20261021/READ-EVENTS.json)、[第三轮读取快照](../../cosmos3-nano-bf16-round3-30pct-20261022/chronology-snapshot-v13/read-provenance.json)、[前次动态时间线](../../cosmos3-nano-bf16-dynamic-20261022/reports/WORKFLOW-CHRONOLOGY.md)。",
"这些链接说明实际使用的历史证据，不把历史Agent读取伪装为本轮并行Agent运行。全量事件时间线、每次读取的路径/行段/observed SHA、命令argv/退出码/日志和失败原因分别由本轮Trace导出。",""])

md.extend(["", "实际源码与动态路由：[DYNAMIC-ROUTE-MAP](DYNAMIC-ROUTE-MAP.md)；全部Thor运行按时间索引：[EXPERIMENT-TIMELINE](EXPERIMENT-TIMELINE.md)；正式每请求新路由计数：[formal-route-audit-v4.json](../results/formal-route-audit-v4.json)。", ""])
md.extend(["", "Trace覆盖边界：21:01:11.763Z的handoff事件已主动披露，某次上下文恢复时三份已加载Skill曾通过旁路直接读取并poll已有进程，随后恢复Trace包装；没有把这些旁路读取事后伪造成read --show观察。Trace记录显式工具事件与用途，不能保证宿主自动拦截全部行为。其余缺失路径/参数失败与修复保留在逐事件时间线，失败读取不算读到了内容。", ""])
(t/"reports").mkdir(exist_ok=True)
(t/"reports/DYNAMIC-FULL-PORT.md").write_text("\n".join(md))
(t/"README.md").write_text("# COSMOS3 Nano BF16 动态完整迁移\n\n"+md[2]+"\n\n[完整报告](reports/DYNAMIC-FULL-PORT.md) · [逐事件时间线](reports/WORKFLOW-CHRONOLOGY.md) · [Agent读取记录](reports/READ-PROVENANCE.md) · [Workflow Trace](reports/WORKFLOW-TRACE.md)\n")
print(json.dumps(outcome,ensure_ascii=False,indent=2))
