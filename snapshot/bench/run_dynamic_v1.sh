#!/bin/bash
set -euo pipefail
harness="$1"
shift
task_root=$(cd "$(dirname "$0")/.." && pwd -P)
export COSMOS_TASK_ROOT="$task_root"
export COSMOS_SOURCE_ROOT="$task_root/baseline/phyai-official"
export PHYAI_KERNEL_CACHE_ROOT="$task_root/cache/phyai_kernel"
export PYTHONPATH="$COSMOS_SOURCE_ROOT/phyai/src:$COSMOS_SOURCE_ROOT/phyai-kernel:$COSMOS_SOURCE_ROOT/phyai-utils-tools/src:$COSMOS_SOURCE_ROOT/phyai-ext/src:$task_root/solution"
exec /home/tomorin/rjc/pi05-profile-20260914/phyai/.venv/bin/python -B "$task_root/bench/$harness" --checkpoint /home/tomorin/rjc/cosmos3-bf16-20260917/models/Cosmos3-Nano-Policy-DROID "$@"
