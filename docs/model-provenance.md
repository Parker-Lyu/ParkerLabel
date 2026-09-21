# Model provenance and ONNX export record

## Upstream source

The source tree under `mobile_sam/` matches MobileSAM commit
`ce9ce32c068c10a21cc96c0e433ce67eac75dcb5` from 2023-07-02. The only
difference in a shared upstream Python file is trailing blank-line formatting
in `mobile_sam/build_sam.py`; Parker Label also adds its export scripts.

The decoder exporter is `mobile_sam/export_mobilesam_decoder.py`. It is based
on Segment Anything commit `02acff7859030229a3ce49b641d47b5b6e0bcbd5`
from 2023-04-15, with imports changed to `mobile_sam`, the default opset
changed to 16, and `dynamo=False` added for the legacy PyTorch ONNX exporter.

## Original checkpoint

- Upstream file: MobileSAM `weights/mobile_sam.pt`
- Size: `40,728,226` bytes
- SHA-256: `6dbb90523a35330fedd7f1d3dfc66f995213d81b29a5ca8108dbcdd4e37d6c2f`

The official upstream checkpoint and the local export input have identical
size and SHA-256.

## Export commands and tools

Run from the repository root with the original checkpoint at
`pretrain/mobile_sam.pt`:

```bash
python -m mobile_sam.export_mobilesam_encoder \
  --checkpoint pretrain/mobile_sam.pt \
  --output pretrain/encoder.onnx

python -m mobile_sam.export_mobilesam_decoder \
  --checkpoint pretrain/mobile_sam.pt \
  --model-type vit_t \
  --opset 16 \
  --output pretrain/decoder.onnx
```

The `models-v2` export environment used Python 3.11, PyTorch 2.13.0,
torchvision 0.28.0, timm 1.0.19, ONNX 1.22.0, and ONNX Runtime 1.29.0. The
decoder uses ONNX IR version 8 and opset 16. The successful command uses
`dynamo=False`; `onnxscript` is not required by this export path.

## Published models-v2 artifacts

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| Original `mobile_sam.pt` | 40,728,226 | `6dbb90523a35330fedd7f1d3dfc66f995213d81b29a5ca8108dbcdd4e37d6c2f` |
| Converted `encoder.onnx` | 28,016,150 | `21e444e2aca6ccae137c89478de457af8dd285b3fb4373804053a9a3d535a12f` |
| Converted `decoder.onnx` | 16,509,691 | `1cdd16b569bdec96a6feddfd5fba704d192a3259e614e8f5c9b5e55c73096b8b` |

The decoder graph contains 1,236 nodes and 136 initializers. It passed ONNX
checker validation and an ONNX Runtime CPU inference during export. Both model
files were uploaded as immutable `models-v2` release assets to GitHub and
Gitee, then downloaded without authentication and verified against the hashes
above. `model-bundle.json` fixes these exact URLs, sizes, and hashes; clients
must not follow a `latest` release alias.
