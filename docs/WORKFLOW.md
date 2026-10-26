# Workflow、时间线与读取记录

本仓库保存动态完整迁移的实际 Workflow Trace。工具记录显式命令、目的、文件读取范围、结果和决策；它不记录模型私有推理，也不证明文件被理解。

| 内容 | 位置 |
| --- | --- |
| 动态完整迁移 Trace | [dynamic-full-port.jsonl](../evidence/workflow/dynamic-full-port.jsonl) |
| 全部读取事件 | [read-events.json](../evidence/workflow/read-events.json) |
| Trace 计数、原始/导出 hash | [trace-provenance.json](../evidence/workflow/trace-provenance.json) |
| 逐事件时间线 | [WORKFLOW-CHRONOLOGY.md](../evidence/reports/WORKFLOW-CHRONOLOGY.md) |
| 读取来源与 Thor 实验索引 | [READ-PROVENANCE.md](../evidence/reports/READ-PROVENANCE.md)、[EXPERIMENT-TIMELINE.md](../evidence/reports/EXPERIMENT-TIMELINE.md) |

历史 Trace ID：`wf-20261023T191907391908Z-63abb6795e`。共 1141 事件，含 238 次读取、386 条命令及对应结束事件。读取中的 tool_output、agent_declared、失败状态均按原记录保留，不将失败读取当成已读取内容。本轮完整动态迁移没有启动子 Agent；更早多 Agent 的历史出处仍在原时间线中明确区分。

## 实际优化过程

1. 加载 Thor 合同和三轮历史，固定官方源码、BF16 字节门槛、动态字段、计时边界。检查原静态优化的条件，保留无法证明安全的官方回退。
2. 迁移在线 VAE prefix、preparation/RMS、packed GEMM 和 exact compact attention；按真实输入形状、布局、设备和 stream 建 plan，禁止跨请求复用输出。不同 CFG 内容关闭 pair CSE。
3. 对新 M 的 Lt 先用实际输入筛选，再以完整模型消融复验。拒绝 M1982 / M3526 的不稳定或退化配置，保留 M1472 四类组合。V3 主语言 29.1609%，未达目标的两窗如实保留。
4. V4 仅加入 M3542 out + down 的组合；单独 out 新布局失败也留档。用新进程官方 oracle 验证 25 + 4 项，再完成两窗主负载和两窗视频/action负载的原始官方对照。
5. 独立标准库读取 raw BF16 storage，复算全部计时；保存实际路由计数、源/二进制 hash、同 trace 归因、拒绝记录和最终报告，finish 原优化 Trace。

完整事件含 UTC / 澳门时间、具体 argv、退出码、读取路径/行段/观察 hash。归档报告中的旧相对链接指向此前不可变提交，较大 capture 或未在本仓库收录的历史证据仍可沿原发布位置查找。

## 本次整理发布

本次使用同一 `thor-kda-workflow`，独立发布 Trace ID 为
`wf-20261026T092108234861Z-f3d5940aa2`，目标为仅向
`crycryout/PhyAIKDACOSMOS3Nano` 发布当前动态 V4。读取使用 `read --show`，
工作命令使用 `run --purpose`，关键版本选择、错误修复、回退及验证结论用 event。
最终在推送和远端 SHA 核对后登记产物、finish 并生成 Markdown 报告；封闭记录保留在任务所在服务器，最终交付中给出路径。

`SOURCE-MANIFEST.json` 保持运行源码原始字节。证据中的个人部署路径仅替换为占位符；原始/发布 SHA 都在 `evidence/ORIGIN-MANIFEST.json` 中。完整历史 Trace 也有不同的导出 hash，不冒称仍与原始文件 hash 一致。

原 Trace 的 `workflow.handoff` 披露了一次恢复上下文时的旁路读取/poll，未事后伪造为 `read --show`。声明、观察和未覆盖动作的边界保持透明。
