# MobileSAM source attribution

The `mobile_sam/` implementation comes from [MobileSAM](https://github.com/ChaoningZhang/MobileSAM). It includes code and notices from [Segment Anything](https://github.com/facebookresearch/segment-anything). The exact upstream revision of this preexisting local copy was not recorded. Keep the original notices in each source file.

`export_mobilesam_decoder.py` is adapted from Segment Anything's ONNX export script. Both upstream projects publish the included code under Apache License 2.0. Their license texts are identical; the copy in [LICENSE](LICENSE) applies to this third-party code.

`modeling/tiny_vit_sam.py` carries Microsoft's TinyViT copyright notice. The upstream [TinyViT license and third-party notices](https://github.com/microsoft/Cream/blob/main/TinyViT/LICENSE) are copied in [TINYVIT_LICENSE](TINYVIT_LICENSE).

`export_mobilesam_encoder.py` was written for Parker Label and is licensed under the root [GPL-3.0-only](../LICENSE) license.
