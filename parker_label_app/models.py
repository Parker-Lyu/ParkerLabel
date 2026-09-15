from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    supercategory: str
    color: tuple[int, int, int]
    description: str = ""
    enabled: bool = True

    @classmethod
    def from_dict(cls, value):
        """Build a category from a JSON-compatible mapping."""
        return cls(
            id=int(value["id"]),
            name=str(value["name"]).strip(),
            supercategory=str(value.get("supercategory", "")).strip(),
            color=tuple(int(channel) for channel in value.get("color", [0, 0, 0])),
            description=str(value.get("description", "")).strip(),
            enabled=bool(value.get("enabled", True)),
        )

    def to_dict(self):
        """Return a JSON-compatible category mapping."""
        return {
            "id": self.id,
            "name": self.name,
            "supercategory": self.supercategory,
            "color": list(self.color),
            "description": self.description,
            "enabled": self.enabled,
        }


@dataclass
class Segment:
    category_id: int
    category_name: str
    color_id: int
    visible: bool = True
    mask: np.ndarray | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_dict(cls, value):
        """Build a segment from a saved annotation mapping."""
        return cls(
            category_id=int(value["category_id"]),
            category_name=str(value["category_name"]),
            color_id=int(value["color_id"]),
        )

    def to_dict(self):
        """Return the persistent representation of a segment."""
        return {
            "category_name": self.category_name,
            "category_id": self.category_id,
            "color_id": self.color_id,
        }


@dataclass
class AnnotationDocument:
    image_path: Path
    image_rgb: np.ndarray
    source_size: tuple[int, int]
    segments: list[Segment] = field(default_factory=list)
    embedding: np.ndarray | None = None
    dirty: bool = False

    def add_segment(self, category: Category, color_id: int):
        """Append a new segment and mark the document as changed."""
        segment = Segment(
            category.id,
            category.name,
            color_id,
            mask=np.zeros(self.image_rgb.shape[:2], dtype=np.uint8),
        )
        self.segments.append(segment)
        self.dirty = True
        return segment

    def remove_segment(self, index: int):
        """Remove a segment and all pixels assigned to it."""
        del self.segments[index]
        self.dirty = True

    def change_segment_color(self, index: int, color_id: int):
        """Replace a segment color identifier without changing its pixels."""
        self.segments[index].color_id = color_id
        self.dirty = True

    def change_segment_category(self, index: int, category: Category):
        """Assign a configured category to a segment."""
        self.segments[index].category_id = category.id
        self.segments[index].category_name = category.name
        self.dirty = True

    def commit_mask(self, index: int, edit_mask: np.ndarray):
        """Commit an edited binary mask to a segment."""
        self.segments[index].mask = edit_mask.astype(np.uint8).copy()
        self.dirty = True

    def composite_mask(self, visible_only=False):
        """Compose instance masks into a color identifier mask for display."""
        result = np.zeros(self.image_rgb.shape[:2], dtype=np.int32)
        for segment in self.segments:
            if visible_only and not segment.visible:
                continue
            if segment.mask is not None:
                result[segment.mask.astype(bool)] = segment.color_id
        return result

    def visible_mask(self):
        """Return a display mask containing only visible instances."""
        return self.composite_mask(visible_only=True)

    def used_color_ids(self):
        """Return every segment color identifier in the document."""
        return {segment.color_id for segment in self.segments}

    def segment_index_for_pixel(self, x: int, y: int):
        """Find the segment index assigned to an image pixel."""
        for index in range(len(self.segments) - 1, -1, -1):
            segment = self.segments[index]
            if segment.visible and segment.mask is not None and segment.mask[y, x]:
                return index
        return None
