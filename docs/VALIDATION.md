# 验证结果、限制和后续接入状态

## 已验收的动态 V4

原实验运行于 Thor ARM64 / SM110，Torch 2.11.0+cu130、CUDA 13.0，BF16、steps=4、CFG=3、flow shift=5、Karras=False、Graph=False。官方源码 pin 为 `75403624f9c8858f347f624e3b032553fa756ac2`。

| 负载 | 配对数 | 配对中位降幅 |
| --- | ---: | ---: |
| 主语言四组长度，合并两独立窗 | 40 | 31.3910748173% |
| action16 | 14 | 32.8482% |
| video17frames | 14 | 30.1963% |
| video320x512 | 14 | 28.9003% |

主负载按总计时计算为 31.5311371813%。报告保留全部慢样本，不合并不同视频形状来构造主结果，也不将过去三轮静态百分比相乘。单长度某些窗口仍低于 30%。

独立官方在未安装候选的新进程中生成 22 份 oracle；最终候选 25 项，加上额外 M3542 的 4 项，action 原始 BF16 storage 全部一致。25 项包含长度 1–512、padding/有效 prefix、换 token/mask/pixels、返回旧长度、新 stream、视频和 action 变化、未知 query 形状，以及 Batch2 官方回退。Attention 另有 12 个 tail、8 次 LRU 淘汰等验证。Graph 兼容回退的原始结果保存在 `evidence/results/graph-fallback-full-port-v4/`。

正式 4 个进程产生 82 对配对、196 个计时输出（含 A/A），每条保留字节门槛及 phase counts。GPU pixels → 在线 VAE → 原始 Engine.step → ready GPU action 是计时边界。

## 2026-10-26 发布复核

本次新增标准库审核工具，逐个核对 1075 份源码快照，并与两个正式进程的运行源 hash 进行 1858 次比较；复核全部 29 份 action 原始 storage 和正式 E2E。读取 zipfile 的 raw storage，不导入 Torch、不反序列化 pickle。新的便携启动器只完成 CPU dry-run 和保护逻辑检查。

[publication-checks.json](../evidence/publication-checks.json) 保存实际复核结果。这些操作重新核对旧证据，不是新的 Thor 测量，也不替代新环境上的 GPU 验证。

## 结论边界

| 问题 | 当前证据 |
| --- | --- |
| 是否全输入、全中间层位级一致？ | 已测 action 字节一致；没有全输入证明或全部中间张量审计 |
| 是否代表真实机器人任务成功率？ | synthetic token IDs / pixels；LIBERO 闭环未完成 |
| 是否每种动态形状都快 30%？ | 否；按 shape 报告，video320x512 为约 28.9% |
| 是否可直接推广到其他硬件/软件版本？ | 仅已记录的 Thor 软件栈；需要重验 |
| 是否已验收 upstream 原生接入？ | 尚未；见下表 |

## 后续 PhyAI 原生接入：未验收

2026-10-25 曾在另一个任务中，将 5 项优化改为默认关闭的 opt-in 路径，基于较新的 PhyAI `f983a8f84684aa7db4dfac7184b7b5c787635978`。该工作与本仓库的 V4 原实验属于两个不同的验证对象。

| 项目 | 记录状态 |
| --- | --- |
| Thor 上 CPU 测试 | 历史记录 231 + 35 + 28 项通过 |
| 3 个原生 kernel 离线 JIT 编译/加载 | 历史记录通过；GPU 数值执行未完成 |
| 原生接入模型 parity / E2E | 未完成 |
| LIBERO 闭环 | 0；环境、权重格式及后续 GPU 验证仍待完成 |
| 阻塞 | 外部 GPU 作业，其后 SSH 超时；独立低频监测继续 |

不把 V4 的 31.3911% 移用为该原生接入的性能。这个仓库发布已验收的动态 V4；尚未验收的原生代码不作为默认入口，也未向 PhyAI 官方提交 PR。
