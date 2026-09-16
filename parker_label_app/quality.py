from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class MaskQuality:
    mask_region_count: int = 0
    hole_count: int = 0
    boxes: tuple[tuple[int, int, int, int], ...] = ()


def inspect_mask_quality(mask, primary_point=None):
    """Inspect foreground regions and enclosed holes in a binary mask."""
    binary = (mask != 0).astype(np.uint8)
    if not np.any(binary):
        return MaskQuality()

    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    component_ids = list(range(1, count))
    primary_id = None
    if primary_point is not None:
        x, y = primary_point
        if 0 <= x < binary.shape[1] and 0 <= y < binary.shape[0]:
            label = int(labels[y, x])
            if label:
                primary_id = label
    if primary_id is None:
        primary_id = max(component_ids, key=lambda index: stats[index, cv2.CC_STAT_AREA])

    boxes = [
        tuple(int(value) for value in stats[index, :4])
        for index in component_ids
        if index != primary_id
    ]

    background = 1 - binary
    hole_count, _, hole_stats, _ = cv2.connectedComponentsWithStats(background, connectivity=8)
    height, width = binary.shape
    enclosed_hole_count = 0
    for index in range(1, hole_count):
        left, top, box_width, box_height = (
            int(value) for value in hole_stats[index, :4]
        )
        if (
            left == 0
            or top == 0
            or left + box_width == width
            or top + box_height == height
        ):
            continue
        enclosed_hole_count += 1
        boxes.append((left, top, box_width, box_height))
    return MaskQuality(len(component_ids), enclosed_hole_count, tuple(boxes))
