
"""Evidence-driven dynamic migration release notes; fail closed on acceptance gates."""
from pathlib import Path
import argparse,difflib,hashlib,json
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);p.add_argument("--parent",type=Path,required=True)
a=p.parse_args();t=a.task;parent=a.parent
def load(rel):return json.loads((t/rel).read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(rel,text):
    dest=t/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
def dump(rel,obj):write(rel,json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
audit=load("results/independent-evidence-audit-v3.json")
release=load("results/candidate-release-v4/validation.json")
attention=load("results/candidate-release-v4/attention-dynamic-validation.json")
paired=load("results/paired-e2e-v3/paired-dynamic-e2e.json")
profile=load("results/profile-v4/profile-metadata.json")
attrib=load("results/profile-analysis-v4/same-trace-physical-attribution.json")
graphs=load("results/graph-fallback-v1/graph-fallback-validation.json")
assert audit["gate_passed"] and audit["storage_comparisons"]==80
assert release["complete"] and release["exact_gate_passed"] and len(release["cases"])==20
assert attention["complete"] and len(attention["rows"])==12 and attention["cache_stats"]["evictions"]==8
assert all(r["byte_equal"] for r in attention["rows"])
assert paired["complete"] and paired["gate_passed"] and len(paired["rows"])==24
assert all(r["reduction_from_medians_pct"]>=30 for r in paired["summary"].values())
assert profile["complete"] and profile["byte_equal"] and graphs["complete"] and graphs["gate_passed"]
runs={}
for tag in ["dynamic-official-model-v2","dynamic-candidate-model-v2","dynamic-candidate-model-v3",
            "dynamic-paired-e2e-v3","dynamic-profile-v4","dynamic-graph-fallback-v1","dynamic-release-actual-v4"]:
    doc=load("results/"+tag+"/run.json")
    assert doc["returncode"]==0 and doc["interference_observed"] is False,tag
    runs[tag]={k:doc[k] for k in ["returncode","interference_observed"]}
    runs[tag].update(before_utc=doc["before"]["utc"],after_utc=doc["after"]["utc"])
checks={}
for lane in ["paired-e2e-v3","candidate-release-v4"]:
    doc=load("results/"+lane+"/runtime-source-hashes.json")
    for row in doc["files"]:
        assert (t/row["path"]).is_file() and sha(t/row["path"])==row["sha256"],(lane,row["path"])
    checks[lane]=dict(files=len(doc["files"]),all_sha256_equal=True)
manifest={}
for folder in ["solution","bench","baseline","contracts"]:
    for path in sorted((t/folder).rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix in [".pyc",".so"]:continue
        name=str(path.relative_to(t))
        if name=="contracts/final-source-hashes.json":continue
        manifest[name]=dict(bytes=path.stat().st_size,sha256=sha(path))
dump("contracts/final-source-hashes.json",manifest)
changed=[];patch=[]
for path in sorted((t/"solution").iterdir()):
    if not path.is_file() or path.suffix not in [".py",".cu",".cpp",".h",".cuh",".json"]:continue
    old=parent/"solution"/path.name
    before=old.read_text() if old.exists() else "";after=path.read_text()
    if before!=after:
        name="solution/"+path.name
        changed.append(dict(path=name,before_sha256=sha(old) if old.exists() else None,after_sha256=sha(path)))
        patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
                     fromfile="r3-v11/"+name if old.exists() else "/dev/null",tofile="dynamic/"+name))
write("patches/dynamic-vs-r3-v11.patch","".join(patch))
dump("contracts/dynamic-final-changes.json",dict(parent="R3-v11",changed_files=changed,
     note="prototype sources retained; timed entry V3; release entry V4"))
summary=dict(complete=True,dynamic_migration_gate_passed=True,
    trace_id="wf-20261022T100635347606Z-ac9c3b5564",
    official_revision="75403624f9c8858f347f624e3b032553fa756ac2",
    parent_entry_sha256=sha(t/"solution/candidate-round3-v11.py"),
    timed_entry="solution/candidate-dynamic-v3.py",timed_entry_sha256=sha(t/"solution/candidate-dynamic-v3.py"),
    release_entry="solution/candidate-dynamic-v4.py",release_entry_sha256=sha(t/"solution/candidate-dynamic-v4.py"),
    dynamic_model_cases=20,model_action_byte_equal=True,attention_tail_cases=12,attention_evictions=8,
    attention_plan_limit=4,independent_storage_audit=80,timed_output_gates=24,
    graph_oracle_cases=2,graph_fallback_byte_equal=True,candidate_graph_speedup_established=False,
    dynamic_e2e=paired["summary"],denominator="original official eager only",
    additional_30pct_over_R3_best_established=False,
    physical_gen_gemms=1152,physical_v40_attention_main_kernels=288,
    gpu_runs=runs,source_checks=checks,environment=load("results/profile-v4/environment.json"),
    limits=["Synthetic token IDs, not robotics task success evaluation.",
      "Tested cases do not cover all legal shapes or arbitrary long sequences.",
      "B>1 and CUDA Graph use original official fallback; no candidate speedup claimed.",
      "Concurrent requests require independent runners.",
      "Checkpoint load/tokenization/pixel preprocessing/optional video decode/robot postprocess excluded."])
dump("results/final-validation-summary.json",summary)
timing=["| 窗口 | 原始官方 | 动态 V3 | E2E 降低 |","| --- | ---: | ---: | ---: |"]
for key,v in paired["summary"].items():
    timing.append(f"| {key} | {v['official_median_ms']:.3f} ms | {v['candidate_median_ms']:.3f} ms | {v['reduction_from_medians_pct']:.4f}% |")
timing="\n".join(timing)
cases=["| 案例 | 正/负 padded tokens | 正/负有效 tokens | 视频 F×H×W / action / batch / stream | 路由 | 门槛 |",
       "| --- | --- | --- | --- | --- | --- |"]
for r in release["cases"]:
    m=r["workload"]
    cases.append(f"| {r['case']} | {m['positive_padded']} / {m['negative_padded']} | {m['positive_real']} / {m['negative_real']} | {m['frames']}×{m['height']}×{m['width']}; A={m['action_chunk']}; B={m['batch']}; {m['stream']} | {r['optimization']['dynamic']['route']} | PASS |")
readme="""# COSMOS3 Nano BF16：动态输入迁移

优化已迁移到按请求变化的语言 token 长度、有效 prefix mask、视频网格和 action 长度，保留原始 PhyAI 语义和 BF16 action 字节门槛。

@TIMING@

分母是**原始官方 eager 路径**。两窗各 6 对，相邻 AB/BA 交替且跨窗反转；24 个计时输出全部通过独立官方字节门槛。该结果不证明“在 R3 最优上再降 30%”。

最终入口为 [candidate-dynamic-v4.py](solution/candidate-dynamic-v4.py)。正式计时冻结在 V3；V4 只修正诊断字段，重新通过 20/20 完整动态案例。动态 attention 12/12 尾块通过并实际发生 8 次 LRU 淘汰。Batch=2 与 CUDA Graph 回退官方，均有实际验证。

1. [动态迁移原理、适用范围、完整验证和接入](reports/DYNAMIC-MIGRATION.md)
2. [逐事件时间线：具体命令、读取行段、失败与选择](reports/WORKFLOW-CHRONOLOGY.md)
3. [工具生成的 Workflow Trace Markdown](reports/WORKFLOW-TRACE.md)
4. [原始 JSONL](results/workflow-trace.jsonl) 与 [机器可读结论](results/final-validation-summary.json)
5. [相对 R3-v11 的补丁](patches/dynamic-vs-r3-v11.patch) 与 [最终源码 SHA256](contracts/final-source-hashes.json)

案例使用 deterministic synthetic token IDs；不代表自然语言任务/机器人成功率。原生 profiler [以无损 gzip 交付](results/profile-v4/candidate-dynamic.trace.json.gz)，原始 JSON 留在本地任务目录。
"""
write("README.md",readme.replace("@TIMING@",timing))
report="""# COSMOS3 Nano BF16 动态迁移：实现、证据与边界

用户关于输入动态的要求成立。此前 R3 主要性能证据使用固定形状；相同 CFG 文本还能获得可证明的重复计算复用。这些数字不能直接推广到动态生产请求。本轮参考 PhyAI 源码迁移，并用不同正负文本重新测量完整请求。

本轮证明动态迁移与当前合同下相对原始官方的收益。历史“相对 R3 最优再降 30%”目标没有同合同的 R3 动态性能分母，本轮不宣布其完成。

## 1. 结果与版本

@TIMING@

每窗 6 对，共 12 对、24 个计时输出。四个 workload：len31_17、len65_97、len128_129、len257_7，均为不同的正/负文本。公式为 `100*(1-median(candidate ready_wall_ms)/median(official ready_wall_ms))`；配对降幅中位数另保存在原始 JSON。

正式计时入口为 `solution/candidate-dynamic-v3.py`，SHA256 `@TIMED_SHA@`。最终交付入口为 `solution/candidate-dynamic-v4.py`，SHA256 `@RELEASE_SHA@`。V4 数值计算全部调用 V3，只修正 disabled CSE wrapper 的诊断字段，且重新通过完整 20 案例。**上表性能仍归冻结 V3。**

官方 pin 为 `75403624f9c8858f347f624e3b032553fa756ac2`。父方案 R3-v11 入口 SHA256 为 `3b638bdf31ebddf5cdac54aba713822efecae33d3838fed1f646720e9d64e786`。动态修改在当前任务的继承副本内完成，不改父任务。

证据：[正式 E2E](../results/paired-e2e-v3/paired-dynamic-e2e.json)、[独立审核](../results/independent-evidence-audit-v3.json)、[最终 V4 门槛](../results/candidate-release-v4/validation.json)。

## 2. 原优化的固定假设

`3542` 是默认 GEN query token 数，来自视频 patch grid 加 action token，**不是语言长度**。默认 latent grid 为 [9,30,52]、patch size 2，故 `9*ceil(30/2)*ceil(52/2)+32=3542`。语言长度改变 UND condition 和有效 KV 长度，不能与 GEN query 数混淆。

原 attention 已有部分按 Q/K shape 建 plan 的逻辑，不能简单说 kernel 只接受一种文本长度。但 source proof、形状特化 GEMM、plan key/生命周期和 fallback 边界并未由固定测试证明覆盖动态请求。本轮逐项处理这些限制。

M=3542 上选出的 CuBLASLt 算法保留原 M/stride guard。视频或 action 变化导致其他 M 时走继承 torch.mm，不把旧算法编号无条件用于新形状。

## 3. 如何按 PhyAI 动态处理迁移

### 3.1 Condition、mask 和请求生命周期

入口仍调用原始 engine.step。官方 runner 每请求 reset 活跃 cond/uncond 状态；有界 condition cache 按内容区别，不能只凭相同长度复用旧内容。重复同内容的 warm case 允许保留官方条件缓存。

官方 `text_mask.sum()` 表示有效 **prefix** 长度。迁移不把带洞 mask 解释为任意 token 选择，也不擅自 unpad 改变官方计算。B>1 分支内有效长度约束保留。padded96_real31、同形状换 token、同形状换 mask、返回先前长度均独立测试。

官方 dynamic=True preparation 处理保留；编译缓存、attention plan、condition cache 彼此独立，都不等同于跨请求复用模型输出。

### 3.2 从固定 query 数迁移到实际几何证明

[dynamic_contract_v2.py](../solution/dynamic_contract_v2.py) 逐次核实 hidden/video geometry、action length、freqs_gen query 长度及每层 cached KV。query 长度由实际 video patch grid 加 action 得到；sound 路径未证明，保留回退。

它接入继承的 source-proof 入口；启用 proof 的路径仍保留 tensor identity/version、route、stream 等约束。不同 CFG 文本时，V3 直接关闭 CSE wrapper，不能声称这些未调用的 proof 检查仍在执行。

### 3.3 动态 attention 和有界内存状态

[compact_attention_dynamic_v2.py](../solution/compact_attention_dynamic_v2.py) 按实际 Q/K/V shapes、strides、dtype、device、stream 建 key，按真实长度重建 offsets/plan。当前优化 ABI 为 BF16、B=1、Q 32 heads / KV 8 heads、head_dim=128、非 causal 官方语义。

LRU 稳态最多 4 plan，每项 workspace 128 MiB；新 plan 建立到旧项退休间可短暂持有第 5 项。淘汰前等待旧 plan 最后使用的 event。清理同样等待 last-use event。Lt workspace 最多两条 stream；第三条 stream 到来时先等待并清理旧资源。

不支持的 rank、dtype、batch、stride、attention semantics、custom mask/context 调用安装前保存的**真正原始官方 forward**。早期继承 closure 指向 R1 优化旧路径的问题已修复。

### 3.4 不同 CFG 文本不再做无效中间 CSE

V2 虽通过精度，但不同正负文本使大部分中间结果无法复用，仍保留大张量并做 GPU 字节比较会引入同步和内存成本。

V3 精确比较请求级 text IDs/masks：不同则关闭 speculative operator memoization，通过已验证 Lt/v40/rounded RMS/VAE 完整计算两支；相同则保留原 pair-local proof 与审计。没有跨 step/request 输出缓存，也没有跳过不同输入的分支。正式性能四组输入都走不同 CFG、完整两支路径。

V4 只更正诊断：disabled wrapper 的零计数不代表物理 nonlinear kernel 为零；明确 counter_scope、实际未调用的 native-signature 检查及全部 nonlinear 计算执行。物理执行另由 native trace 证明，V4 重新跑完整门槛。

### 3.5 请求级官方回退与 Graph

入口在安装前保存原始 transformer/module methods、MLP activation、runner forward 和 fusion methods。Graph、batch/rank、dtype/device、非 policy 等未支持请求回官方；返回时恢复候选模式并失效旧 graph/cache。

Batch=2 已完整执行并通过 byte gate。Graph 测试先在**未安装候选**时跑原始官方 Graph 两种长度 11/7、33/19，再安装 V4 执行官方回退，两个 action 均逐字节一致。官方 cond/uncond 各有真实 capture/replay；长度切换后 captures 由 1 增至 2。候选返回恢复模式会清理 graphs，因此候选结果中 graphs_after_request 为空。这里证明兼容回退，未测候选 Graph 加速。

证据：[Graph oracle 与回退](../results/graph-fallback-v1/graph-fallback-validation.json)。

## 4. 动态模型精度矩阵

门槛为输出 finite BF16、shape 正确、原始 BF16 storage 字节与独立原始官方输出完全相等。V2、V3、最终 V4 分别通过 20/20，没有放宽 tolerance。

@CASES@

long512 后紧邻的 repeat_long512_warm 保留官方 condition cache，可见 condition_encode=0；正式计时每请求清理条件状态，两支均冷编码 condition_encode=2，不混用 warm 结果。

[独立审核脚本](../bench/audit_evidence_v3.py) 用 zipfile 读取 .pt 唯一原始 tensor storage，不导入 Torch、不执行 pickle。它对官方、V2、V3、最终 V4 共 80 份 storage 核对实际字节、shape 对应字节数和 SHA256；再核对 24 个计时行、phase counts、AB/BA 顺序及中位数。

### Attention 尾块与淘汰

12 组 (Q,KV)：(1,1)、(31,17)、(63,64)、(64,65)、(65,129)、(127,191)、(128,257)、(129,513)、(257,319)、(3542,3543)、(3542,3573)、(1472,1505)。

要求真实优化 dispatch 增加、12 次 plan miss、8 次 LRU eviction 后字节仍一致。custom mask、batch2、dtype、非 unit last stride 另验证调用原始官方。早期“全 fallback 但相等”的样本已拒绝，不算优化 kernel 证据。

证据：[最终尾块/回退](../results/candidate-release-v4/attention-dynamic-validation.json)。

## 5. E2E 合同与边界

主指标 ready_wall_ms：GPU pixels -> 在线 causal VAE -> 原始 engine.step -> UND -> 4 steps×2 CFG GEN -> action head -> ready GPU BF16 action。CUDA event 和 host submit 分别保存，不替换主指标。

两边同 checkpoint、BF16、Thor2、steps=4、guidance=3、flow shift=5、Karras=False、Graph=False。相邻 pair 用同 pixels/request/seed；每边先两次不计时完整 warmup。顺序按 (window+pair)%2 交替且跨窗反转。每个计时行均实际有 VAE=1、engine_step=1、condition_encode=2、denoiser=8，24 个输出均对独立官方 archive 做 byte gate。

同既有合同，排除 checkpoint load、tokenization、pixel preprocessing、optional video decode、robot postprocess。因此不等于从文本/相机采集到机器人执行的应用总延迟。案例为 deterministic synthetic token IDs，不是自然语言理解或机器人成功率评估。

硬件为 Thor2 haruhikage、aarch64、NVIDIA Thor SM110、driver580.00；Torch2.11.0+cu130/CUDA13，显式 CUDA13 ptxas。H800 仅做本地源码/CPU分析。未改其他任务、进程、时钟或driver。通过 gate 的所有正式 Thor run exit=0 且 interference_observed=false；完整 telemetry 保存在对应 run.json。

两窗在一次受控进程内完成，不代表跨天或真实流量统计置信区间。没有穷举任意长文本、全部合法shape组合、weight hot swap或长期并发服务。full 接口按完整请求串行同步使用；并发请求需独立 runner。B>1/Graph 走兼容回退，不宣称同样收益。当前结果也不证明相对 R3 最优再降30%。

## 6. Native profiler 证明实际完整计算

先两次 len31_17 完整 warmup，再 profile len65_97 的完整 V4 请求。CPU+CUDA、record_shapes、with_stack；输出通过独立官方 byte gate。profile 时间不进入 speedup。

CUDA correlation -> runtime/driver -> 同线程显式 CPU scope 的实际映射为：

| 量 | 实测 |
| --- | ---: |
| GEN GEMM scopes / 主kernel | 1152 / 1152 |
| GEN attention scopes / v40主kernel | 288 / 288 |
| attention scope内所有kernel | 870 |
| 全trace CUDA kernel | 7869 |
| GEN GEMM kernel duration sum | 3251.436 ms |
| v40 attention主kernel duration sum | 843.877 ms |
| 全kernel duration sum | 5079.158 ms |
| kernel busy interval union | 5073.172 ms |
| GPU activity busy interval union | 5075.164 ms |

attention scope还包含扩展V的填充/拷贝和plan元数据，不能把全部870次写成288次。kernel sum、busy union、未profile ready-wall E2E为不同量，不相减当作可消除时间。

Workflow PhyAI离线分析器实际运行，保留 kernel/overlap/fusion 三表。通用heuristic把v40 FMHA名称误归memory，本报告根据源码/实名修正为attention。工具没有找到达到阈值的可信overlap或source-backed fusion机会，不编造收益或MFU。

证据：[Workflow三表](../results/profile-analysis-v4/workflow-profiler-three-tables.txt)、[同trace归因](../results/profile-analysis-v4/SAME-TRACE-ATTRIBUTION.md)、[逐kernel CSV](../results/profile-analysis-v4/same-trace-kernel-attribution.csv)、[profile元数据](../results/profile-v4/profile-metadata.json)。

原始trace166157257 bytes，本地保留；gzip13346378 bytes。解压SHA256为 dd5b971d3f12e90c3d9d8b017ad0ddc5484916ee95cf5e4382e7b10e99554cb2，与原JSON完全相等。[压缩证明](../results/profile-v4/trace-compression.json)。

## 7. 拒绝、错误与修复

| 位置 | 原因 | 修复/处理 |
| --- | --- | --- |
| 首次task传输 | SSH255 | 读旧Thor任务继承源，fresh SSH传小增量，核hash |
| 首次官方oracle | bundled ptxas-blackwell不识别sm_110a | 两个PTXAS selector显式CUDA13，重跑oracle |
| prototype尾块 | scale浮点表达式末位不同，全fallback | 拒绝优化证据；匹配官方1/sqrt(128)，强制真实dispatch/eviction |
| ordinary官方context | cumulative offsets误当custom mask | 对照single_prefill语义修正；不扩展arbitrary-hole语义 |
| V1 batch2回退 | 对只读last_request_stats赋值 | V2 mutate dictionary，重跑20案例 |
| V2不同CFG的CSE成本 | 大中间结果与无效字节比较 | V3按请求文本/mask决定关闭，完整两支 |
| V3诊断 | disabled wrapper零计数易误读 | V4更正统计，重跑20案例 |
| 独立审核V2 | 假定每窗都official先行 | V3按(window+pair)%2修复，原数据不改 |
| 名为validate_dynamic_model_v4的脚本 | import仍指V3 | 只算V3重验；v5导入common_v4，实际结果candidate-release-v4 |
| 同trace分析V1 | 假定attention scope仅1kernel | V2区分主kernel和填充/拷贝辅助kernel |
| gzip校验 | Python3.10无hashlib.file_digest | 改分块SHA读回，原JSON/gzip保留且完全相等 |
| upstream CPU suite | 系统Python缺pytest，3个import error | 既有pytest环境：31 adapter、124 upstream unittest通过 |
| 多次路径/行段定位 | 文件名不存在或超EOF | 记录失败，按观察到的路径和行段读取 |
| 报告生成首次工具调用 | JS模板反引号解析错误 | 未执行shell/文件变更；改安全文本构造 |

所有prototype、失败run/stderr及修复事件保留。详见[完整时间线](WORKFLOW-CHRONOLOGY.md)，不能按文件名推断某版本通过。

## 8. Agent如何使用Workflow

1. 实际start锁定动态迁移任务、目的、目标和parent trace；以read --show读取Skill、Thor合同、工具路由、官方动态源码和历史R3证据，记录路径、具体行段与内容hash。
2. 依据官方语义选择guard/plan/cache/fallback；先独立官方oracle，再逐版数值gate。每条有界命令经run --purpose记录argv/cwd/时长/退出码/stdout/stderr，关键拒绝/修复/选择经event。
3. 要求真实优化dispatch和淘汰，避免“全fallback也相等”；模型字节门槛通过后才做非profile的相邻配对E2E，profile另证实际kernel而非作为加速数字。
4. 对source/binary及原始输出做独立hash审核；如实区分V3计时、V4诊断与Graph官方回退，保留所有失败。
5. artifact登记源码、patch、精度、性能、trace、profile与报告；finish陈述本轮成功范围及未证明的R3再降30%。发布使用单独delivery trace，不向已finish优化trace继续追加。

本轮没有派子Agent，读取均为root的实际workflow.read事件；历史多Agent记录属于前轮独立报告。Trace记录可观察工具输出和显式目的/决定，不声称记录隐藏思考或自动证明阅读理解。

## 9. 接入与复现

将整个solution及其baseline/accepted继承目录一起保留，不只复制入口。使用同官方pin、模型与ARM64/SM110环境，设置COSMOS_TASK_ROOT和task-local caches：

```python
import importlib.util
import os, sys
from pathlib import Path

task = Path(os.environ["COSMOS_TASK_ROOT"])
sys.path.insert(0, str(task / "solution"))
spec = importlib.util.spec_from_file_location(
    "cosmos_dynamic", task / "solution/candidate-dynamic-v4.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
control = module.install(engine.entry.transformer, vae, engine)
try:
    # 每次request携带实际ids/masks/video_shape/action_chunk。
    action = control.full(pixels, request, vae_runner, engine)
finally:
    control.close()
```

权重/device/config替换后调用control.invalidate_cache()；多个并发请求使用独立runner。full是完整请求的串行同步入口。

实际环境、所有argv与source/binary manifests均保留。启动器bench/run_dynamic_v3.sh引用现有Thor ARM64 Python与checkpoint的绝对路径，换机器需显式修改这两个部署路径并重新验证；不能在H800上复跑后冒称Thor结果。

复现最终门槛：用tools/thor.py run执行bench/run_dynamic_v3.sh validate_dynamic_model_v5.py，参数backend=candidate、reference=results/official-v2，输出使用新的结果目录。正式性能则执行paired_dynamic_e2e_v3.py，pairs=6，选择上述四个case，输出使用新目录。Graph回退执行validate_graph_fallback_v1.py并启用--cuda-graph。每条仍应由当前Workflow Trace的run --purpose包装。

独立官方reference应先在无候选安装的backend=official进程生成，源码与原始action已保存。本目录的bench/audit_evidence_v3.py可在本机标准库环境独立审核保存结果。

## 10. 证据索引

事前合同：contracts/dynamic-contract-v1.json。继承源：inherited-sources.json与seed-source-hashes.json。变更：contracts/dynamic-final-changes.json、patches/dynamic-vs-r3-v11.patch。交付源码：contracts/final-source-hashes.json。

正式计时source/binary：results/paired-e2e-v3/runtime-source-hashes.json与runtime-binary-hashes.json。运行前后/遥测：results/dynamic-paired-e2e-v3/run.json。最终V4、oracle、profile与Graph分别保存原始运行和二进制manifest。

Trace ID：wf-20261022T100635347606Z-ac9c3b5564。
JSONL：[results/workflow-trace.jsonl](../results/workflow-trace.jsonl)。
工具Markdown：[WORKFLOW-TRACE.md](WORKFLOW-TRACE.md)。
逐事件时间线：[WORKFLOW-CHRONOLOGY.md](WORKFLOW-CHRONOLOGY.md)。
"""
report=report.replace("@TIMING@",timing).replace("@CASES@","\n".join(cases))
report=report.replace("@TIMED_SHA@",summary["timed_entry_sha256"]).replace("@RELEASE_SHA@",summary["release_entry_sha256"])
write("reports/DYNAMIC-MIGRATION.md",report)
print(json.dumps(dict(report=str(t/"reports/DYNAMIC-MIGRATION.md"),solution_changes=len(changed),
    source_files=len(manifest),runtime_source_checks=checks),ensure_ascii=False,indent=2))
