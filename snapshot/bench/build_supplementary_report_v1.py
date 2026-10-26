"""Summarize audited continuation experiments without changing formal V3 evidence."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
runs=["sampler-residency-screen-v1-attempt2","request-residency-screen-v4-window0",
      "request-coefficients-screen-v1-window0","key-ahead-independent-window1"]
md=["# 动态路径续跑：完整模型消融与拒绝证据","",
    "当前正式入口仍为 candidate-full-port-v3.py。本文件记录后续探索；筛选数据不替代四个正式独立窗口。主语言40对配对中位降幅29.1609308%，按总耗时降幅28.8252885%；各主窗口稳定30%的目标尚未成立。",
    "", "所有实验保持BF16、4步、CFG3、不同正负文本、每请求冷UND、在线VAE到ready GPU action边界。完整请求均实际VAE1、engine_step1、condition_encode2、denoiser8。准备或复制发生在计时区间内。",
    "", "## 按运行时间排序的实验","",
    "| UTC开始 → 结束 | 实验 / 变量 | 实际完整请求 | 配对数 | 配对中位改善 | 总耗时改善 | 结论 |",
    "| --- | --- | ---: | ---: | ---: | ---: | --- |"]
audits=[]
for tag in runs:
    folder=t/"results"/tag
    audit=json.loads((folder/"independent-screen-audit.json").read_text())
    run=json.loads((folder/"run.json").read_text())
    assert audit["complete"] and run["returncode"]==0 and not run["interference_observed"]
    audits.append(dict(tag=tag,audit=audit))
    for row in audit["results"]:
        value=lambda key:f'{row[key]:.6f}%' if key in row else "未计时"
        verdict="只通过首窗，独立复验未过，拒绝晋升" if row["variant"]=="key_ahead" else "未过1%门槛，拒绝晋升"
        if not row["gate_passed"]:verdict="实际常数复用门槛失败；不使用性能"
        md.append(f"| {run['before']['utc']} → {run['after']['utc']} | {tag}<br>{row['variant']} | {audit['rows']} | {row['pairs']} | {value('paired_median_reduction_pct')} | {value('reduction_from_total_time_pct')} | {verdict} |")
md+=["", "统计中的正数表示比相邻V3完整请求快，负数表示慢。各运行的完整请求数包含warmup，同一运行多变体共享该总数。进入复验需所有byte/物理dispatch门槛通过，且配对中位与总耗时改善均≥1%。没有因接近门槛改变阈值，也没有把弱收益相加成新候选。",
    "", "## 精度与运行时证据","",
    "所有这些运行的完整模型BF16 action均与独立原官方archive逐storage byte相等，所有物理GEN计数均1152 GEMM/288 attention。系数预计算另有48项逐步随机velocity序列与原UniPC byte对照，覆盖1/2/4/5/8步、linear/Karras和两种张量rank；这些数值通过没有被当作性能通过。",
    "", "## 关键修复和拒绝","",
    "1. 首次远程入口误传bench/前缀，run_with_binary_manifest_v8.py:6在加载模型之前拒绝；用新tag改为文件名重试，保留原失败run。",
    "2. constants v1将cuda与cuda:0直接比较，20次tensor构造均未命中代理；BF16正确但actual-dispatch门槛失败。v2正规化device index后，14次one复用、6次half复用门槛通过，完整模型仍没有稳定性能收益。",
    "3. 未执行的cold-key bypass源码被主动拒绝：不填condition_cache会改变后续请求缓存收益。实际测试改为保留原内容key/LRU/active branch语义，把4次token/mask host tuple复制移到请求开始。第二进程换token长度且BA/AB反转，未重现首窗收益。",
    "4. 原GPU FP32 UniPC系数与linalg.solve仅提前至同请求set_timesteps，且只在本请求video/action两sampler间复用；所有sample相关BF16操作顺序保留。数值全过，性能未过，未叠加进最终入口。",
    "", "## 相反权重布局筛选",""]
layout=t/"results/opposite-layout-main-screen-v1/independent-screen-audit.json"
if layout.exists():
    d=json.loads(layout.read_text())
    md+=["", "| GEN类别 | 原布局row-major | 新布局row-major | 新Torch/原Lt单核耗时比 | 通过3类byte门槛后选中 |", "| --- | --- | --- | ---: | --- |"]
    for row in d["rows"]:
        md.append(f"| {row['category']} | {row['original_b_row']} | {row['new_b_row']} | {row['opposite_torch_ratio']:.6f} | {row['selected'] is not None} |")
    md+=["", "只有attention output投影的新row-major权重布局和torch.mm进入完整模型筛选；单核约12.04%改善不作为E2E结论。36层重新pack多占1,207,959,552 bytes（1.125GiB），只作用于M3542；其他M保持原动态fallback。对应captures保留Thor的results/opposite-layout-main-screen-v1/captures，选择清单和源/二进制hash已取回。"]
md+=["", "## 可复查入口","",
    "- [原V3正式报告](DYNAMIC-FULL-PORT.md)",
    "- [当前原始Workflow Trace](../results/workflow-trace.jsonl)",
    "- 每组results/<tag>/independent-screen-audit.json保存无Torch独立复算；原始sampler-residency-e2e.json、run.json、环境与source/binary清单并存。",
    "", "Trace ID: wf-20261023T191907391908Z-63abb6795e。",
    "", "本文件为续跑阶段的已审核事实快照；主Trace仍活动。生成UTC："+datetime.now(timezone.utc).isoformat(), ""]
(t/"reports/SUPPLEMENTARY-EXPERIMENTS.md").write_text("\n".join(md))
print(json.dumps(dict(report=str(t/"reports/SUPPLEMENTARY-EXPERIMENTS.md"),audited_runs=len(audits)),ensure_ascii=False))
