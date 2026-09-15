from pathlib import Path
from time import perf_counter

import numpy as np
import onnxruntime


class SegmentationEngine:
    def __init__(self, encoder_path: Path, decoder_path: Path, target_size: int = 1024):
        """Initialize model paths without loading runtime sessions."""
        self.encoder_path = Path(encoder_path)
        self.decoder_path = Path(decoder_path)
        self.target_size = target_size
        self.encoder_session = None
        self.decoder_session = None
        self.encoder_input_name = None

    def _load_encoder(self):
        """Load the encoder session on first use."""
        if self.encoder_session is not None:
            return
        if not self.encoder_path.exists():
            raise FileNotFoundError(f"Missing encoder model: {self.encoder_path}")
        self.encoder_session = onnxruntime.InferenceSession(
            str(self.encoder_path), providers=["CPUExecutionProvider"]
        )
        self.encoder_input_name = self.encoder_session.get_inputs()[0].name

    def _load_decoder(self):
        """Load the decoder session on first use."""
        if self.decoder_session is not None:
            return
        if not self.decoder_path.exists():
            raise FileNotFoundError(f"Missing decoder model: {self.decoder_path}")
        self.decoder_session = onnxruntime.InferenceSession(str(self.decoder_path))

    def encode(self, image_rgb: np.ndarray):
        """Encode a resized RGB image into a MobileSAM embedding."""
        self._load_encoder()
        height, width = image_rgb.shape[:2]
        padded = np.zeros((self.target_size, self.target_size, 3), dtype=np.uint8)
        padded[:height, :width] = image_rgb
        tensor = padded.transpose(2, 0, 1)[None].astype(np.float32)
        tensor -= np.array([123.675, 116.28, 103.53], dtype=np.float32)[None, :, None, None]
        tensor /= np.array([58.395, 57.12, 57.375], dtype=np.float32)[None, :, None, None]
        started_at = perf_counter()
        embedding = self.encoder_session.run(None, {self.encoder_input_name: tensor})[0].astype(np.float32)
        elapsed_ms = (perf_counter() - started_at) * 1000
        if embedding.shape != (1, 256, 64, 64):
            raise ValueError(f"Unexpected encoder output shape: {embedding.shape}")
        return embedding, elapsed_ms

    def predict(self, embedding, image_shape, points, labels, previous_logits=None):
        """Predict a binary segment mask from positive and negative points."""
        self._load_decoder()
        coordinates = np.asarray(points, dtype=np.float32)[None]
        point_labels = np.asarray(labels, dtype=np.float32)[None]
        coordinates = np.concatenate([coordinates, np.zeros((1, 1, 2), dtype=np.float32)], axis=1)
        point_labels = np.concatenate([point_labels, -np.ones((1, 1), dtype=np.float32)], axis=1)
        height, width = image_shape
        scale = self.target_size / max(height, width)
        coordinates[..., 0] *= int(width * scale + 0.5) / width
        coordinates[..., 1] *= int(height * scale + 0.5) / height
        if previous_logits is None:
            mask_input = np.zeros((1, 1, 256, 256), dtype=np.float32)
            has_mask_input = np.zeros(1, dtype=np.float32)
        else:
            mask_input = previous_logits
            has_mask_input = np.ones(1, dtype=np.float32)
        inputs = {
            "image_embeddings": embedding,
            "point_coords": coordinates,
            "point_labels": point_labels,
            "mask_input": mask_input,
            "has_mask_input": has_mask_input,
            "orig_im_size": np.asarray(image_shape, dtype=np.float32),
        }
        started_at = perf_counter()
        masks, _, logits = self.decoder_session.run(None, inputs)
        elapsed_ms = (perf_counter() - started_at) * 1000
        return (masks[0, 0] > 0).astype(np.uint8), logits, elapsed_ms
