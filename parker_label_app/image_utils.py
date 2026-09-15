from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def resize_longest_side(image_rgb: np.ndarray, target_size: int):
    """Resize an RGB image so its longest side matches the target size."""
    height, width = image_rgb.shape[:2]
    scale = target_size / max(height, width)
    target_width = int(round(width * scale))
    target_height = int(round(height * scale))
    return cv2.resize(image_rgb, (target_width, target_height), interpolation=cv2.INTER_LINEAR)


def load_rgb_image(path: Path, target_size: int):
    """Load an image as RGB and return its resized and source dimensions."""
    with Image.open(path) as image:
        source = np.asarray(image.convert("RGB"))
    source_size = source.shape[:2]
    return resize_longest_side(source, target_size), source_size


def color_id_to_rgb(color_id: int):
    """Convert a packed segment identifier to an RGB tuple."""
    return color_id % 256, (color_id // 256) % 256, color_id // 65536


def id_mask_to_rgb(mask_id: np.ndarray):
    """Convert packed segment identifiers into an RGB mask."""
    result = np.empty((*mask_id.shape, 3), dtype=np.uint8)
    result[:, :, 0] = mask_id % 256
    result[:, :, 1] = (mask_id // 256) % 256
    result[:, :, 2] = mask_id // 65536
    return result


def qimage_from_rgb(image_rgb: np.ndarray):
    """Create a detached Qt image from a contiguous RGB array."""
    from PyQt5.QtGui import QImage

    contiguous = np.ascontiguousarray(image_rgb)
    height, width = contiguous.shape[:2]
    return QImage(contiguous.data, width, height, width * 3, QImage.Format_RGB888).copy()
