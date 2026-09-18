from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class EditSnapshot:
    edit_mask: np.ndarray | None
    previous_logits: np.ndarray | None
    manual_constraints: np.ndarray | None
    prompt_points: list
    prompt_labels: list
    edit_dirty: bool
    metadata_dirty: bool
    metadata_snapshot: tuple | None
    document_dirty: bool
    category_id: int
    category_name: str
    color_id: int


def arrays_equal(first, second):
    if first is None or second is None:
        return first is second
    return np.array_equal(first, second)


def low_res_manual_constraints(
    manual_constraints: np.ndarray,
    model_input_size: int = 1024,
    low_res_size: int = 256,
):
    height, width = manual_constraints.shape
    low_width = min(
        low_res_size,
        max(1, int(round(width * low_res_size / model_input_size))),
    )
    low_height = min(
        low_res_size,
        max(1, int(round(height * low_res_size / model_input_size))),
    )
    foreground = cv2.resize(
        (manual_constraints > 0).astype(np.float32),
        (low_width, low_height),
        interpolation=cv2.INTER_AREA,
    )
    background = cv2.resize(
        (manual_constraints < 0).astype(np.float32),
        (low_width, low_height),
        interpolation=cv2.INTER_AREA,
    )
    result = np.zeros((low_res_size, low_res_size), dtype=np.int8)
    active = result[:low_height, :low_width]
    active[foreground > background] = 1
    active[background > foreground] = -1
    return result


def build_effective_mask_input(
    previous_logits: np.ndarray | None,
    manual_constraints: np.ndarray | None,
    model_input_size: int = 1024,
    low_res_size: int = 256,
    logit_strength: float = 10.0,
):
    if manual_constraints is None or not np.any(manual_constraints):
        return previous_logits
    if previous_logits is None:
        logits = np.zeros((1, 1, low_res_size, low_res_size), dtype=np.float32)
    else:
        expected_shape = (1, 1, low_res_size, low_res_size)
        if previous_logits.shape != expected_shape:
            raise ValueError(
                f"Unexpected previous logits shape: {previous_logits.shape}"
            )
        logits = previous_logits.astype(np.float32, copy=True)
    constraints = low_res_manual_constraints(
        manual_constraints,
        model_input_size=model_input_size,
        low_res_size=low_res_size,
    )
    logits[0, 0][constraints > 0] = logit_strength
    logits[0, 0][constraints < 0] = -logit_strength
    return logits


def apply_manual_constraints(mask: np.ndarray, manual_constraints: np.ndarray | None):
    if manual_constraints is None or not np.any(manual_constraints):
        return mask
    if mask.shape != manual_constraints.shape:
        raise ValueError(
            f"Mask shape {mask.shape} does not match manual constraints "
            f"{manual_constraints.shape}"
        )
    result = mask.astype(np.uint8, copy=True)
    result[manual_constraints > 0] = 1
    result[manual_constraints < 0] = 0
    return result
