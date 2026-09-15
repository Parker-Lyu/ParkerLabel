import json
import os
import tempfile
from pathlib import Path

from .models import Category


class CategoryConfigError(ValueError):
    pass


class CategoryStore:
    def __init__(self, path: Path):
        """Initialize a category store backed by one local JSON file."""
        self.path = Path(path)

    def load(self):
        """Load and validate categories from local JSON."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise CategoryConfigError(f"Unable to read category configuration: {error}") from error
        raw_categories = payload.get("categories") if isinstance(payload, dict) else payload
        if not isinstance(raw_categories, list):
            raise CategoryConfigError("Category configuration must contain a categories list")
        try:
            categories = [Category.from_dict(value) for value in raw_categories]
        except (KeyError, TypeError, ValueError) as error:
            raise CategoryConfigError(f"Invalid category entry: {error}") from error
        self.validate(categories)
        return categories

    def save(self, categories):
        """Validate and atomically save categories to local JSON."""
        categories = list(categories)
        self.validate(categories)
        payload = {
            "schema_version": 1,
            "preset": "coco-detection-2017",
            "categories": [category.to_dict() for category in categories],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{self.path.name}.", suffix=".tmp", dir=self.path.parent
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary_path, self.path)
        except Exception:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
            raise

    @staticmethod
    def validate(categories):
        """Reject incomplete, duplicate, or out-of-range category values."""
        if not categories:
            raise CategoryConfigError("At least one category is required")
        ids = set()
        names = set()
        for category in categories:
            if category.id < 0:
                raise CategoryConfigError("Category identifiers must be non-negative")
            if not category.name:
                raise CategoryConfigError("Category names cannot be empty")
            normalized_name = category.name.casefold()
            if category.id in ids:
                raise CategoryConfigError(f"Duplicate category identifier: {category.id}")
            if normalized_name in names:
                raise CategoryConfigError(f"Duplicate category name: {category.name}")
            ids.add(category.id)
            names.add(normalized_name)

    def enabled(self):
        """Return enabled categories in stored order."""
        return [category for category in self.load() if category.enabled]

    def by_name(self):
        """Return enabled categories keyed by exact name."""
        return {category.name: category for category in self.enabled()}
