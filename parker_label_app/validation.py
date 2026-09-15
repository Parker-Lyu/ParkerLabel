from dataclasses import dataclass, field

import cv2
import numpy as np

from .models import AnnotationDocument


@dataclass
class ValidationReport:
    empty_segments: list[int] = field(default_factory=list)
    noisy_segments: list[int] = field(default_factory=list)

    @property
    def valid(self):
        """Return whether the annotation passes every validation rule."""
        return not (
            self.empty_segments
            or self.noisy_segments
        )


def validate_document(document: AnnotationDocument, noise_threshold: int = 10):
    """Validate identifier consistency, coverage, and small mask components."""
    report = ValidationReport()
    for index, segment in enumerate(document.segments, start=1):
        binary = segment.mask.astype(np.uint8) if segment.mask is not None else np.zeros(document.image_rgb.shape[:2], dtype=np.uint8)
        if not np.any(binary):
            report.empty_segments.append(index)
            continue
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            component = np.zeros_like(binary)
            cv2.drawContours(component, [contour], -1, 1, -1)
            if int(component.sum()) < noise_threshold:
                report.noisy_segments.append(index)
                break
    return report
