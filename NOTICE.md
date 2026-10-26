# Source and license notices

Pinned PhyAI source in snapshot/baseline/phyai-official/ is preserved at
revision 75403624f9c8858f347f624e3b032553fa756ac2, including its MIT license.
Runtime source and inherited headers are copied without formatting or numerical changes.

CUDA/CUTLASS-derived headers retain their original copyright and license text.
xxHash retains its BSD 2-Clause license at
snapshot/baseline/phyai-official/phyai-ext/third_party/xxhash/LICENSE.
FlashInfer, CUTLASS, TVM FFI, Triton and NVIDIA CUDA are external dependencies
with their respective licenses. No model weights or compiled extensions are included.

SOURCE-MANIFEST.json identifies every byte-identical snapshot file.
evidence/ORIGIN-MANIFEST.json records original and exported evidence hashes.
Historical paths in exported evidence use $TASK_ROOT, $WORKFLOW_ROOT,
$LOCAL_HOME, $THOR_HOME and $THOR_HOST; no numeric result was changed.
Historical deployment launchers remain in the snapshot for provenance;
use scripts/run_thor.py for configurable Python and checkpoint paths.
