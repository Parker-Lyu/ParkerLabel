import cv2
import numpy as np


def find_mask_quality_boxes(mask, primary_point=None):
    """Return tight boxes for foreground fragments and enclosed holes."""
    binary = (mask != 0).astype(np.uint8)
    if not np.any(binary):
        return []

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
        boxes.append((left, top, box_width, box_height))
    return boxes
