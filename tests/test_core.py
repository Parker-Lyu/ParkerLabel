import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from parker_label_app.annotation_io import (
    AnnotationRepository,
    decode_uncompressed_rle,
    encode_uncompressed_rle,
)
from parker_label_app.category_store import CategoryStore
from parker_label_app.models import AnnotationDocument, Category
from parker_label_app.validation import validate_document


class CategoryStoreTests(unittest.TestCase):
    def test_default_configuration_contains_coco_detection_categories(self):
        """Verify the default local configuration contains the COCO detection set."""
        path = Path(__file__).resolve().parent.parent / "config" / "categories.json"
        categories = CategoryStore(path).load()
        self.assertEqual(len(categories), 80)
        self.assertEqual(categories[0].name, "person")
        self.assertEqual(categories[-1].name, "toothbrush")


class RleTests(unittest.TestCase):
    def test_round_trip_preserves_binary_mask(self):
        """Verify uncompressed COCO RLE preserves mask shape and pixels."""
        mask = np.zeros((7, 9), dtype=np.uint8)
        mask[0:3, 0:2] = 1
        mask[4:7, 5:9] = 1
        encoded = encode_uncompressed_rle(mask)
        decoded = decode_uncompressed_rle(encoded)
        np.testing.assert_array_equal(decoded, mask)

    def test_round_trip_supports_first_foreground_pixel(self):
        """Verify RLE begins with a zero-length background run when required."""
        mask = np.ones((2, 2), dtype=np.uint8)
        encoded = encode_uncompressed_rle(mask)
        self.assertEqual(encoded["counts"][0], 0)
        np.testing.assert_array_equal(decode_uncompressed_rle(encoded), mask)


class DocumentTests(unittest.TestCase):
    def make_document(self, image_path):
        """Create an in-memory document for instance mask tests."""
        image = np.zeros((8, 10, 3), dtype=np.uint8)
        return AnnotationDocument(
            image_path=image_path,
            image_rgb=image,
            source_size=(8, 10),
        )

    def test_independent_instance_masks_can_overlap(self):
        """Verify separate instance masks retain overlapping pixels."""
        document = self.make_document(Path("image.jpg"))
        first = document.add_segment(Category(1, "person", "person", (200, 10, 10)), 100)
        second = document.add_segment(Category(3, "car", "vehicle", (10, 10, 200)), 200)
        first_mask = np.zeros((8, 10), dtype=np.uint8)
        second_mask = np.zeros((8, 10), dtype=np.uint8)
        first_mask[1:5, 1:5] = 1
        second_mask[3:7, 3:8] = 1
        document.commit_mask(0, first_mask)
        document.commit_mask(1, second_mask)
        self.assertEqual(first.mask[3, 3], 1)
        self.assertEqual(second.mask[3, 3], 1)
        self.assertEqual(document.segment_index_for_pixel(3, 3), 1)

    def test_repository_round_trip_preserves_overlapping_instances(self):
        """Verify saved JSON preserves masks, boxes, and overlap independently."""
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "sample.jpg"
            cv2.imwrite(str(image_path), np.zeros((8, 10, 3), dtype=np.uint8))
            document = self.make_document(image_path)
            document.add_segment(Category(1, "person", "person", (200, 10, 10)), 100)
            document.add_segment(Category(3, "car", "vehicle", (10, 10, 200)), 200)
            first_mask = np.zeros((8, 10), dtype=np.uint8)
            second_mask = np.zeros((8, 10), dtype=np.uint8)
            first_mask[1:5, 1:5] = 1
            second_mask[3:7, 3:8] = 1
            document.commit_mask(0, first_mask)
            document.commit_mask(1, second_mask)
            repository = AnnotationRepository(target_size=10)
            repository.save(document)
            with image_path.with_suffix(".json").open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["format"], "parker-label-instance-v1")
            preview = cv2.imread(str(image_path.parent / "sample.mask.png"), cv2.IMREAD_COLOR)
            self.assertIsNotNone(preview)
            self.assertEqual(preview.shape[:2], (8, 10))
            self.assertEqual(preview[3, 3].tolist(), [0, 0, 200])
            self.assertEqual(payload["annotations"][0]["bbox"], [1, 1, 4, 4])
            loaded = repository.open(image_path)
            self.assertEqual(len(loaded.segments), 2)
            self.assertEqual(loaded.segments[0].mask[3, 3], 1)
            self.assertEqual(loaded.segments[1].mask[3, 3], 1)

    def test_repository_rejects_unsupported_annotation_format(self):
        """Verify the repository does not load legacy annotation data."""
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "legacy.jpg"
            cv2.imwrite(str(image_path), np.zeros((8, 10, 3), dtype=np.uint8))
            with image_path.with_suffix(".json").open("w", encoding="utf-8") as handle:
                json.dump({"file_name": image_path.name, "annotations": []}, handle)
            with self.assertRaisesRegex(ValueError, "Unsupported annotation format"):
                AnnotationRepository(target_size=10).open(image_path)

    def test_repository_saves_geometry_at_source_resolution(self):
        """Verify saved boxes and masks use original image coordinates."""
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "large.jpg"
            cv2.imwrite(str(image_path), np.zeros((16, 20, 3), dtype=np.uint8))
            document = self.make_document(image_path)
            document.source_size = (16, 20)
            document.add_segment(Category(1, "person", "person", (200, 10, 10)), 100)
            mask = np.zeros((8, 10), dtype=np.uint8)
            mask[1:5, 1:5] = 1
            document.commit_mask(0, mask)
            repository = AnnotationRepository(target_size=10)
            repository.save(document)
            with image_path.with_suffix(".json").open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["image"]["width"], 20)
            self.assertEqual(payload["image"]["height"], 16)
            self.assertEqual(payload["annotations"][0]["bbox"], [2, 2, 8, 8])
            self.assertEqual(payload["annotations"][0]["segmentation"]["size"], [16, 20])
            preview = cv2.imread(str(image_path.parent / "large.mask.png"), cv2.IMREAD_COLOR)
            self.assertEqual(preview.shape[:2], (16, 20))

    def test_validation_does_not_require_background_annotation(self):
        """Verify instance validation permits unlabeled background pixels."""
        document = self.make_document(Path("image.jpg"))
        document.add_segment(Category(1, "person", "person", (200, 10, 10)), 100)
        mask = np.zeros((8, 10), dtype=np.uint8)
        mask[1:5, 1:5] = 1
        document.commit_mask(0, mask)
        report = validate_document(document)
        self.assertTrue(report.valid)


if __name__ == "__main__":
    unittest.main()
