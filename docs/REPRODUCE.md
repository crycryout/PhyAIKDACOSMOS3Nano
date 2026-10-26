# Thor 复现说明

所有 GPU 测量均在 Thor SM110 上运行。本机 H800 的 CPU 审核或 dry-run 不产生 Thor 性能结论。

## 正式入口与条件

| 模式 | 实际 harness | 固定条件 |
| --- | --- | --- |
| oracle / validate | `validate_full_port_final_v4.py` | 原始官方独立进程 / 候选 V4；22 / 25 项 |
| benchmark | `paired_full_port_v5.py` | 官方 baseline；每形状/模式两次 warmup；相邻 AB/BA，第二窗口反转 |
| extra-oracle / extra-validate | `validate_extra_main_paths_v5.py` | 2 份独立 M3542 oracle / 4 项候选含新 stream |

不要误用 `paired_full_port_v4.py`：其默认导入的是较早的 V3。

主负载默认 20 对/窗；`--suite shapes` 默认 21 对/窗，每种形状 7 对。每窗先做 4 对 A/A，绝对中位漂移必须 ≤3%。正式执行保留 primary CUDA context 到进程退出，并输出 runtime source / mapped binary hashes。

~~~bash
python3 scripts/run_thor.py benchmark --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --reference results/oracle-new \
  --suite shapes --out results/shapes-new-window0 --window-index 0

python3 scripts/run_thor.py benchmark --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --reference results/oracle-new \
  --suite shapes --out results/shapes-new-window1 --window-index 1
~~~

额外 M3542 测试：

~~~bash
python3 scripts/run_thor.py extra-oracle --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --out results/extra-oracle-new

python3 scripts/run_thor.py extra-validate --python "$THOR_PYTHON" \
  --checkpoint "$COSMOS_CHECKPOINT" --reference results/extra-oracle-new \
  --out results/extra-validation-new
~~~

## 环境与权重

启动器将 vendored PhyAI 的模块放在 PYTHONPATH 首位，设置 task-local CUDA / Triton / TorchInductor / PhyAI kernel 缓存，并明确使用 CUDA 13.0 / SM110a。它不安装依赖、不调整时钟、不处理其他人的进程。

下载模型需要遵守模型发布者的访问和许可要求。仓库未包含权重，也未验证任意下载 revision 与历史权重逐字节相同。重新实验时固定同一份权重，先用它生成新 oracle，再在相同条件下测候选。历史 oracle 只能用于其已记录的模型/输入条件。

源码中的实验 JIT 路径保持原样：Triton、TVM FFI CUDA，以及 g++ 按需构建 cuBLASLt / signature 适配器；不依赖本次分发任何预编译二进制。JIT 时间和权重打包不计入报告的 warm E2E，须单独保留。

## 直接接入同版 PhyAI

使用已固定的 `Engine`、transformer、VAE 和 runner 实例；导入或初始化前按启动器建立模块路径。通过 `importlib.util.spec_from_file_location` 加载最终入口后：

~~~python
control = candidate_module.install(engine.entry.transformer, vae, engine)
try:
    actions = control.full(pixels, request, vae_runner, engine)
finally:
    control.close()
~~~

`full` 包含在线 VAE，并为请求写入 conditioning latents。不要在外部预先运行 VAE 后再把结果当作同一 E2E。每个 runner 使用独立 control；更换权重后重建 control。不要将这些猴子补丁直接推广到未验证的 upstream HEAD。

## 检查本次发布内容

~~~bash
python3 scripts/audit_release.py
python3 scripts/run_thor.py --help
~~~

前者核验本仓库存档，不是对新 `snapshot/results/` 的自动验收器；新实验仍须审核其验证 JSON、raw actions、A/A、全部配对、环境及源码/二进制清单。
