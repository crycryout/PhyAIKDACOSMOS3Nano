# 动态路径的实际执行

入口是 [candidate-full-port-v4.py](../snapshot/solution/candidate-full-port-v4.py)。它继承动态 V3 的运行时 guard，并仅增加经过完整 E2E 复验的 M3542 两类 GEMM 路由。

| 优化 | 动态行为 |
| --- | --- |
| 因果 VAE prefix | 每请求按 conditioning frame indexes 计算实际消费前缀，保留在线 VAE |
| Preparation / residual + RMS | 运行时形状，保留官方 BF16 中间舍入 |
| GEN GEMM | M3542：out 权重 row-major 后 torch.mm，down 原 packed layout 的 torch.mm；M1472：四类已验证 Lt 配置；其他 M 继承动态实现 |
| Compact attention v40 | 真实 Q/K/V shape、stride、dtype、device、stream 建 plan；LRU 4；尾块和不支持场景保留回退 |
| CFG pair CSE | 仅正负 token 与 mask 字节完全相同时允许；不同内容执行完整双分支；无跨请求输出缓存 |

GEN 的 M 来自视频 patch 和 action 长度；文本长度影响 UND 和 attention KV，不应将两者混用。相同 token 长度也不能证明两个 CFG 分支相同。

~~~mermaid
flowchart TD
    A["每请求 pixels、token / mask、video / action、stream"] --> G{"Batch1、BF16 CUDA、policy、Graph off？"}
    G -->|否| O["原始官方 VAE + Engine.step"]
    G -->|是| C{"正负 token / mask 字节相同？"}
    C -->|是| S["逐 pair 证明后复用"]
    C -->|否| D["完整 2 UND + 8 GEN"]
    S --> V["动态 VAE prefix / preparation / RMS"]
    D --> V
    V --> M["按真实 M、布局和 stream 分派 GEMM"]
    M --> K["动态 attention plan / tail / 官方回退"]
    K --> Y["ready GPU BF16 actions"]
~~~

普通不同 CFG 的正式请求为 1152 次物理 GEN GEMM、288 次 attention。same-CFG 已测为 576 / 144；该特殊收益不用于估计不同文本的性能。

M1982 和 M3526 的新增 Lt 配置在完整模型上退化或未稳定通过复验，因此最终继续原动态路径。M3542 单独 out 新布局也曾退化，只有 out + down 的组合通过双窗复验。选择、失败和回退均可在 [时间线](../evidence/reports/EXPERIMENT-TIMELINE.md) 查到。

V4 新增 36 份权重 pack，共 1,207,959,552 bytes（1.125 GiB）；这是增量内存成本，初始化后复用。未做并发容量评估。共用 runner 不支持并发请求；切换权重需要重建 control。

mask 延续官方的有效前缀语义，不新增任意 mask-hole 语义。Batch2 和 Graph 是官方回退的兼容性证据；优化收益仅针对实际命中的已验证路径。
