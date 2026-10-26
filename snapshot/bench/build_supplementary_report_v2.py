"""Finalize the supplemental record using audited E2E layout experiments."""
from pathlib import Path
import argparse,json
p=argparse.ArgumentParser();p.add_argument("--task",type=Path,required=True);a=p.parse_args();t=a.task
body=(t/"reports/SUPPLEMENTARY-EXPERIMENTS-V3.md").read_text()
body=body.replace("当前正式入口仍为 candidate-full-port-v3.py。本文件记录后续探索；筛选数据不替代四个正式独立窗口。主语言40对配对中位降幅29.1609308%，按总耗时降幅28.8252885%；各主窗口稳定30%的目标尚未成立。","V3主语言40对配对中位降幅29.1609308%，按总耗时降幅28.8252885%，没有稳定达到30%。本文件保留后续探索的完整拒绝证据；最终采用的V4组合与直接官方对照结论见完整报告。")
body=body.replace("[原V3正式报告](DYNAMIC-FULL-PORT.md)","[原V3正式报告](DYNAMIC-FULL-PORT-V3.md) · [最终V4报告](DYNAMIC-FULL-PORT.md)")
body=body.replace("本文件为续跑阶段的已审核事实快照；主Trace仍活动。生成UTC：","原始续跑阶段快照生成UTC：")
lines=["","## V4最终采用的布局组合：完整模型双进程筛选","","| UTC开始 → 结束 | 独立运行 / 变体 | 完整请求 | 配对数 | 相对V3配对中位改善 | 总计时改善 | 门槛 |","| --- | --- | ---: | ---: | ---: | ---: | --- |"]
for tag in ("opposite-layout-e2e-screen-v1-window0","opposite-layout-e2e-confirm-v2-window1"):
    folder=t/"results"/tag
    audit=json.loads((folder/"independent-screen-audit.json").read_text())
    run=json.loads((folder/"run.json").read_text())
    assert audit["complete"] and audit["all_bytes_phases_dispatch_passed"] and run["returncode"]==0 and not run["interference_observed"]
    for r in audit["results"]:
        verdict="通过初筛；仅组合被最终V4采用" if r["accepted_for_confirmation"] else "完整E2E退化，拒绝"
        lines.append(f"| {run['before']['utc']} → {run['after']['utc']} | {tag}<br>{r['variant']} | {audit['rows']} | {r['pairs']} | {r['paired_median_reduction_pct']:.6f}% | {r['reduction_from_total_time_pct']:.6f}% | {verdict} |")
lines += ["","44次完整请求包括不计时warmup。上表收益相对V3，只用于选择；最终对官方的百分比由新的四个独立正式窗口直接计算，不使用乘法外推。单核筛选、新布局单项失败和组合成功全部保留。","","V4完整质量25/25及额外4/4独立raw BF16 storage门槛通过。same-CFG原CSE执行器的extension dispatch为0；不同CFG和两个新stream为576。首次额外测试误预期288已在新harness修复，候选字节未变；原失败目录也一并发布。","","完整append-only Trace及最终finish状态见[WORKFLOW-TRACE](WORKFLOW-TRACE.md)。"]
(t/"reports/SUPPLEMENTARY-EXPERIMENTS.md").write_text(body+"\n".join(lines)+"\n")
print(json.dumps(dict(report=str(t/"reports/SUPPLEMENTARY-EXPERIMENTS.md"),layout_runs=2,rows=44),ensure_ascii=False))
