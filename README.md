# PhyAI KDA · COSMOS3 Nano BF16 动态优化

已验收版本：**Dynamic Full Port V4**。在 Thor SM110 上，相对锁定版本的原始 PhyAI，主动态语言负载的 **40 对配对中位 E2E 降幅为 31.3911%**。正式数据、完整源码依赖和输出字节证据都保存在本仓库。

| 证据 | 结果 |
| --- | --- |
| 官方基线 | `mingti-org/phyai@75403624f9c8858f347f624e3b032553fa756ac2` |
| 主语言负载 | 31/17、65/97、128/129、257/7 正负 token 长度，逐请求切换 |
| 两个独立主窗口 | 20 对 / 窗，配对中位降幅 32.7964% / 30.7416% |
| 合并主结果 | 官方中位 8647.674 ms；V4 中位 5902.821 ms；配对中位降幅 31.3911% |
| 正确性与计时存档 | 25 + 4 项完整模型 action 字节一致；82 对正式配对、196 个计时输出均通过字节门槛 |

上述两种中位耗时的比值对应 31.7409%；31.3911% 是逐 pair 计算降幅后取中位数，两者定义不同。官方 baseline 是上述固定 commit，并非实时 HEAD。数据来自 2026-10-24 的 Thor 实验；2026-10-26 发布阶段仅进行了 CPU 证据复核。

## 1. 找到实现

默认入口为 [candidate-full-port-v4.py](snapshot/solution/candidate-full-port-v4.py)，接口是 `install(transformer, vae, engine)`、`control.full(...)` 和 `control.close()`。

| 路径 | 内容 |
| --- | --- |
| [snapshot/solution](snapshot/solution) | 最终 V4、动态路由、JIT CUDA 源码和继承链 |
| [snapshot/baseline](snapshot/baseline) | 固定官方源码、继承实现和原始 oracle |
| [scripts/run_thor.py](scripts/run_thor.py) | 可指定 Python / checkpoint 的复现入口 |
| [evidence/results](evidence/results) | 正式逐请求计时、25 + 4 项精度数据、原始 action 和审计 |
| [evidence/workflow](evidence/workflow) | 全部 1141 个优化事件、238 条读取记录及导出哈希 |

保留旧版本是为了完整的导入依赖和历史。不要把旧候选或旧部署 shell 当作默认入口。`SOURCE-MANIFEST.json` 逐文件固定全部 1075 份快照；发布没有格式化或修改数值源码。

## 2. 在 CPU 上核对存档

~~~bash
git clone https://github.com/crycryout/PhyAIKDACOSMOS3Nano.git
cd PhyAIKDACOSMOS3Nano
python3 scripts/audit_release.py
~~~

只需 Python 标准库，不导入 Torch、不执行 pickle，也不启动 GPU。它重算全部 82 对计时、检查 196 个输出门槛、直接比较 29 份 action 的 raw BF16 storage，并验证源码和 Workflow 哈希。原始 `.pt` 是小型输出夹具，权重不随仓库分发。

## 3. 在 Thor 上复现

需要 ARM64 Thor SM110、Python ≥3.12、Torch 2.11.0+cu130、Transformers 5.8.1、FlashInfer 0.6.17、CUDA 13.0（`/usr/local/cuda-13.0`）、g++，以及官方依赖的 Triton / TVM FFI / CuTe 工具链。使用已有验证环境；新环境安装参考固定源码的 [README](snapshot/baseline/phyai-official/README.md)。权重使用 `Cosmos3-Nano-Policy-DROID`，在 oracle 和候选之间保持相同文件。

~~~bash
export THOR_PYTHON=/absolute/path/to/thor/environment/bin/python
export COSMOS_CHECKPOINT=/absolute/path/to/Cosmos3-Nano-Policy-DROID

# 在任意主机仅预览命令；不接触 GPU。
python3 scripts/run_thor.py oracle --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --out results/oracle-new --dry-run
~~~

在空闲 Thor 上，先生成未安装候选的独立官方 oracle，再验证候选：

~~~bash
python3 scripts/run_thor.py oracle --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --out results/oracle-new

python3 scripts/run_thor.py validate --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --reference results/oracle-new \
  --out results/validation-new
~~~

每条命令启动独立模型进程。主 E2E 的两个窗口也必须分开启动：

~~~bash
python3 scripts/run_thor.py benchmark --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --reference results/oracle-new \
  --out results/main-new-window0 --window-index 0 --pairs 20

python3 scripts/run_thor.py benchmark --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --reference results/oracle-new \
  --out results/main-new-window1 --window-index 1 --pairs 20
~~~

输出位于 `snapshot/results/`，JIT 缓存位于 `snapshot/cache/`，均不纳入 Git。非 Thor 或有外部 GPU 进程时，启动器拒绝运行；输出目录必须为空。新启动器通过了本次 CPU 检查和 dry-run，其 GPU 调用保留原正式 harness，尚未在本次发布中重新执行。

更多形状及额外 M3542 测试见 [复现说明](docs/REPRODUCE.md)。

## 4. 理解适用范围

E2E 从 GPU pixels 开始，包含在线 VAE、原始 `Engine.step`、UND 和 4 步双 CFG，直到 GPU BF16 actions ready；排除加载权重、tokenization、CPU 图像预处理、可选视频解码和机器人后处理。固定 BF16、CFG 3、flow shift 5、Karras=False、Graph=False。

动态 token / mask、视频形状、action 长度和 stream 都有验证。未知形状保留动态计算或官方回退；Batch2 和 CUDA Graph 使用官方兼容回退。`video320x512` 的配对中位降幅为 28.9003%，不承诺每个形状或每条请求均达到 30%。

字节一致结论覆盖已测 action，不是逐层中间张量或所有输入的数学证明。数据使用 synthetic token IDs / pixels，**未完成 LIBERO 闭环成功率验证**。后续官方原生 API 集成也尚未完成 Thor GPU 验收，不能套用这里的 31.3911%；状态见 [验证边界](docs/VALIDATION.md)。

## 5. 查证来源

[动态实现与回退](docs/DYNAMIC-PATH.md) · [验证与代价](docs/VALIDATION.md) · [Workflow 与时间线](docs/WORKFLOW.md) · [历史完整报告](evidence/reports/DYNAMIC-FULL-PORT.md) · [许可证](LICENSE) · [来源清单](evidence/ORIGIN-MANIFEST.json)

本仓库是独立的可复现研究快照。后续是否向 PhyAI 官方提交 PR，由仓库所有者决定。
