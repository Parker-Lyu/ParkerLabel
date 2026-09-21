"""Export the MobileSAM TinyViT image encoder to a fixed-shape ONNX model.

This script is only needed when regenerating the deployment artifact. The GUI
does not import PyTorch or mobile_sam; it consumes pretrain/encoder.onnx.
"""

import argparse
import os

import torch

from mobile_sam import sam_model_registry


class EncoderOnly(torch.nn.Module):
    def __init__(self, sam_model):
        super().__init__()
        self.image_encoder = sam_model.image_encoder

    def forward(self, image):
        return self.image_encoder(image)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="pretrain/mobile_sam.pt")
    parser.add_argument("--output", default="pretrain/encoder.onnx")
    args = parser.parse_args()

    model = sam_model_registry["vit_t"](checkpoint=args.checkpoint).eval()
    encoder = EncoderOnly(model).eval()
    dummy = torch.zeros(1, 3, 1024, 1024, dtype=torch.float32)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with torch.no_grad():
        torch.onnx.export(
            encoder,
            dummy,
            args.output,
            input_names=["image"],
            output_names=["image_embeddings"],
            opset_version=17,
            do_constant_folding=True,
            dynamo=False,
        )
    print("Exported {}".format(args.output))


if __name__ == "__main__":
    main()
