import json
from pathlib import Path

import cv2
import numpy as np

from .image_utils import id_mask_to_rgb, load_rgb_image, rgb_to_color_id
from .models import AnnotationDocument, Segment


def artifact_paths(image_path: Path):
    """Return embedding, mask, and annotation paths for an image."""
    stem = image_path.with_suffix("")
    return Path(f"{stem}.npy"), Path(f"{stem}.mask.png"), Path(f"{stem}.json")


def encode_uncompressed_rle(mask: np.ndarray):
    """Encode a binary mask as COCO-compatible uncompressed RLE."""
    pixels = np.asarray(mask, dtype=np.uint8).reshape(-1, order="F")
    pixels = (pixels != 0).astype(np.uint8)
    changes = np.flatnonzero(pixels[1:] != pixels[:-1]) + 1
    counts = np.diff(np.concatenate(([0], changes, [pixels.size]))).astype(int).tolist()
    if pixels.size and pixels[0]:
        counts.insert(0, 0)
    return {"size": [int(mask.shape[0]), int(mask.shape[1])], "counts": counts}


def decode_uncompressed_rle(value):
    """Decode a COCO-compatible uncompressed RLE mask."""
    height, width = (int(item) for item in value["size"])
    pixels = np.zeros(height * width, dtype=np.uint8)
    offset = 0
    foreground = False
    for count in value["counts"]:
        count = int(count)
        if foreground:
            pixels[offset : offset + count] = 1
        offset += count
        foreground = not foreground
    if offset != pixels.size:
        raise ValueError("RLE length does not match its declared size")
    return pixels.reshape((height, width), order="F")


def mask_geometry(mask: np.ndarray):
    """Return COCO bounding box and area values for a binary mask."""
    ys, xs = np.where(mask != 0)
    if xs.size == 0:
        return [0, 0, 0, 0], 0
    left = int(xs.min())
    top = int(ys.min())
    width = int(xs.max() - left + 1)
    height = int(ys.max() - top + 1)
    return [left, top, width, height], int(xs.size)


class AnnotationRepository:
    def __init__(self, target_size: int = 1024):
        """Initialize annotation persistence with a model image size."""
        self.target_size = target_size

    def open(self, image_path: Path):
        """Load an image and any matching annotation artifacts."""
        image_path = Path(image_path)
        image_rgb, source_size = load_rgb_image(image_path, self.target_size)
        embedding_path, mask_path, annotation_path = artifact_paths(image_path)
        mask_id = np.zeros(image_rgb.shape[:2], dtype=np.int32)
        segments = []
        if mask_path.exists() and annotation_path.exists():
            mask_bgr = cv2.imread(str(mask_path), cv2.IMREAD_COLOR)
            if mask_bgr is None:
                raise ValueError(f"Unable to read mask: {mask_path}")
            mask_rgb = cv2.cvtColor(mask_bgr, cv2.COLOR_BGR2RGB)
            if mask_rgb.shape[:2] != image_rgb.shape[:2]:
                mask_rgb = cv2.resize(
                    mask_rgb,
                    (image_rgb.shape[1], image_rgb.shape[0]),
                    interpolation=cv2.INTER_NEAREST,
                )
            mask_id = rgb_to_color_id(mask_rgb)
            with annotation_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            raw_segments = payload.get("annotations", [])
            segments = [Segment.from_dict(value) for value in raw_segments]
            for segment, value in zip(segments, raw_segments):
                segmentation = value.get("segmentation")
                if isinstance(segmentation, dict) and isinstance(segmentation.get("counts"), list):
                    decoded = decode_uncompressed_rle(segmentation)
                    if decoded.shape != image_rgb.shape[:2]:
                        decoded = cv2.resize(
                            decoded,
                            (image_rgb.shape[1], image_rgb.shape[0]),
                            interpolation=cv2.INTER_NEAREST,
                        )
                    segment.mask = decoded.astype(np.uint8)
                else:
                    segment.mask = (mask_id == segment.color_id).astype(np.uint8)
        embedding = None
        if embedding_path.exists():
            embedding = np.load(embedding_path).astype(np.float32)
            if embedding.shape != (1, 256, 64, 64):
                raise ValueError(f"Unexpected embedding shape: {embedding.shape}")
        document = AnnotationDocument(
            image_path=image_path,
            image_rgb=image_rgb,
            source_size=source_size,
            segments=segments,
            embedding=embedding,
        )
        return document

    def save(self, document: AnnotationDocument):
        """Save the color mask and JSON annotations beside the source image."""
        _, mask_path, annotation_path = artifact_paths(document.image_path)
        source_height, source_width = document.source_size
        compatibility_mask = cv2.resize(
            document.composite_mask(),
            (source_width, source_height),
            interpolation=cv2.INTER_NEAREST,
        )
        mask_rgb = id_mask_to_rgb(compatibility_mask)
        if not cv2.imwrite(str(mask_path), cv2.cvtColor(mask_rgb, cv2.COLOR_RGB2BGR)):
            raise OSError(f"Unable to write mask: {mask_path}")
        annotations = []
        for index, segment in enumerate(document.segments, start=1):
            working_mask = segment.mask if segment.mask is not None else np.zeros(document.image_rgb.shape[:2], dtype=np.uint8)
            mask = cv2.resize(
                working_mask,
                (source_width, source_height),
                interpolation=cv2.INTER_NEAREST,
            )
            bbox, area = mask_geometry(mask)
            annotation = segment.to_dict()
            annotation.update(
                {
                    "id": index,
                    "image_id": 1,
                    "bbox": bbox,
                    "area": area,
                    "iscrowd": 0,
                    "segmentation": encode_uncompressed_rle(mask),
                }
            )
            annotations.append(annotation)
        payload = {
            "format": "coco-instance-per-image-v1",
            "image": {
                "id": 1,
                "file_name": document.image_path.name,
                "width": int(source_width),
                "height": int(source_height),
            },
            "annotations": annotations,
        }
        with annotation_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        document.dirty = False

    def save_embedding(self, document: AnnotationDocument):
        """Save an image embedding beside its source image."""
        embedding_path, _, _ = artifact_paths(document.image_path)
        np.save(embedding_path, document.embedding)
