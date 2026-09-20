import json
import struct
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
from parker_label_app.category_store import (
    CategoryConfigError,
    CategoryConfigManager,
    CategoryStore,
)
from parker_label_app.image_utils import load_rgb_image
from parker_label_app.models import AnnotationDocument, Category


class CategoryStoreTests(unittest.TestCase):
    def test_default_configuration_contains_coco_detection_categories(self):
        """Verify the default local configuration contains the COCO detection set."""
        path = Path(__file__).resolve().parent.parent / "config" / "default-coco.json"
        categories = CategoryStore(path).load()
        self.assertEqual(len(categories), 80)
        self.assertEqual(categories[0].name, "person")
        self.assertEqual(categories[-1].name, "toothbrush")
        self.assertNotIn("color", categories[0].to_dict())

    def test_configuration_requires_exact_fields_and_boolean_enabled(self):
        """Reject missing, extra, and loosely typed category fields."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "categories.json"
            payload = {
                "schema_version": 6,
                "uuid": "11111111-1111-4111-8111-111111111111",
                "created_at": "2026-09-18T09:52:35+08:00",
                "sha256": "a" * 64,
                "parent_version_uuid": None,
                "categories": [
                    {
                        "id": 1,
                        "name": "person",
                        "supercategory": "person",
                        "description": "",
                        "enabled": "false",
                    }
                ]
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CategoryConfigError, "enabled 必须是布尔值"):
                CategoryStore(path).load()
            payload["categories"][0]["color"] = "red"
            payload["categories"][0]["enabled"] = True
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CategoryConfigError, "未知字段：color"):
                CategoryStore(path).load()

    def test_manager_keeps_existing_configs_readonly_and_persists_named_default(self):
        """Create a draft, save it repeatedly, freeze it, and reload its UUID."""
        builtin = Path(__file__).resolve().parent.parent / "config" / "default-coco.json"
        with tempfile.TemporaryDirectory() as directory:
            manager = CategoryConfigManager(builtin, Path(directory))
            self.assertEqual(manager.default_config_id(), manager.BUILTIN_ID)
            categories = manager.load(manager.BUILTIN_ID)
            with self.assertRaisesRegex(CategoryConfigError, "不可修改"):
                manager.builtin_store.save(
                    manager.BUILTIN_ID,
                    "2026-09-18T09:52:35+08:00",
                    categories,
                )
            config_id = "11111111-1111-4111-8111-111111111111"
            manager.create("道路场景", config_id, categories[:2])
            created_at = manager.load_data(config_id).created_at
            manager.save_draft(config_id, categories[:3])
            self.assertEqual(manager.load_data(config_id).created_at, created_at)
            manager.set_default(config_id)
            manager.freeze(config_id)
            with self.assertRaisesRegex(CategoryConfigError, "不可修改"):
                manager.save_draft(config_id, categories[:4])
            reloaded = CategoryConfigManager(builtin, Path(directory))
            self.assertEqual(reloaded.default_config_id(), config_id)
            self.assertEqual(reloaded.configuration(config_id).name, "道路场景")
            self.assertEqual(len(reloaded.load(config_id)), 3)

    def test_manager_rejects_duplicate_names_ignoring_case(self):
        """Keep user configuration display names unique."""
        builtin = Path(__file__).resolve().parent.parent / "config" / "default-coco.json"
        with tempfile.TemporaryDirectory() as directory:
            manager = CategoryConfigManager(builtin, Path(directory))
            categories = manager.load(manager.BUILTIN_ID)[:1]
            manager.create(
                "Road", "11111111-1111-4111-8111-111111111111", categories
            )
            with self.assertRaisesRegex(CategoryConfigError, "配置名称重复"):
                manager.create(
                    "road", "22222222-2222-4222-8222-222222222222", categories
                )

    def test_manager_rejects_duplicate_configuration_uuids(self):
        """Reject two configuration files that claim the same identity."""
        builtin = Path(__file__).resolve().parent.parent / "config" / "default-coco.json"
        with tempfile.TemporaryDirectory() as directory:
            manager = CategoryConfigManager(builtin, Path(directory))
            categories = manager.load(manager.BUILTIN_ID)[:1]
            config_id = "11111111-1111-4111-8111-111111111111"
            manager.create("Road", config_id, categories)
            source = Path(directory) / "Road.json"
            duplicate = Path(directory) / "Duplicate.json"
            duplicate.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            with self.assertRaisesRegex(CategoryConfigError, "uuid 重复"):
                manager.configurations()

    def test_content_hash_ignores_json_formatting(self):
        """Hash semantic configuration content instead of raw file bytes."""
        builtin = Path(__file__).resolve().parent.parent / "config" / "default-coco.json"
        with tempfile.TemporaryDirectory() as directory:
            manager = CategoryConfigManager(builtin, Path(directory))
            categories = manager.load(manager.BUILTIN_ID)[:1]
            config_id = "11111111-1111-4111-8111-111111111111"
            manager.create("Road", config_id, categories)
            path = Path(directory) / "Road.json"
            before = manager.load_data(config_id).content_hash
            payload = json.loads(path.read_text(encoding="utf-8"))
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(manager.load_data(config_id).content_hash, before)


class ImageLoadingTests(unittest.TestCase):
    def test_loads_color_grayscale_and_transparent_images_from_unicode_paths(self):
        color_bgr = np.array([[[10, 20, 30], [40, 50, 60]]], dtype=np.uint8)
        grayscale = np.array([[10, 90]], dtype=np.uint8)
        transparent_bgra = np.array([[[10, 20, 30, 0], [40, 50, 60, 255]]], dtype=np.uint8)
        cases = [
            (color_bgr, cv2.cvtColor(color_bgr, cv2.COLOR_BGR2RGB)),
            (grayscale, cv2.cvtColor(grayscale, cv2.COLOR_GRAY2RGB)),
            (transparent_bgra, cv2.cvtColor(transparent_bgra[:, :, :3], cv2.COLOR_BGR2RGB)),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for index, (pixels, expected) in enumerate(cases):
                with self.subTest(index=index):
                    path = Path(directory) / f"测试 图像 {index}.png"
                    path.write_bytes(cv2.imencode(".png", pixels)[1].tobytes())
                    image, source_size = load_rgb_image(path, 2)
                    self.assertEqual(source_size, (1, 2))
                    np.testing.assert_array_equal(image, expected)

    def test_jpeg_exif_orientation_does_not_change_annotation_coordinates(self):
        pixels = np.array(
            [
                [[0, 0, 255], [0, 255, 0], [255, 0, 0]],
                [[255, 255, 255], [0, 0, 0], [0, 255, 255]],
            ],
            dtype=np.uint8,
        )
        encoded = cv2.imencode(".jpg", pixels)[1].tobytes()
        original = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
        tiff = (
            b"II*\x00\x08\x00\x00\x00\x01\x00\x12\x01\x03\x00"
            b"\x01\x00\x00\x00\x06\x00\x00\x00\x00\x00\x00\x00"
        )
        payload = b"Exif\x00\x00" + tiff
        encoded = encoded[:2] + b"\xff\xe1" + struct.pack(">H", len(payload) + 2) + payload + encoded[2:]
        rotated = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
        self.assertEqual(rotated.shape[:2], (3, 2))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rotated.jpg"
            path.write_bytes(encoded)
            image, source_size = load_rgb_image(path, 3)
        self.assertEqual(source_size, (2, 3))
        np.testing.assert_array_equal(image, cv2.cvtColor(original, cv2.COLOR_BGR2RGB))

    def test_rejects_invalid_images(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.png"
            for content in (b"", b"not an image"):
                path.write_bytes(content)
                with self.assertRaisesRegex(ValueError, "Cannot decode image"):
                    load_rgb_image(path, 1024)


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
        first = document.add_segment(Category(1, "person", "person"), 100)
        second = document.add_segment(Category(3, "car", "vehicle"), 200)
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
            document.add_segment(Category(1, "person", "person"), 100)
            document.add_segment(Category(3, "car", "vehicle"), 200)
            first_mask = np.zeros((8, 10), dtype=np.uint8)
            second_mask = np.zeros((8, 10), dtype=np.uint8)
            first_mask[1:5, 1:5] = 1
            second_mask[3:7, 3:8] = 1
            document.commit_mask(0, first_mask)
            document.commit_mask(1, second_mask)
            repository = AnnotationRepository(target_size=10)
            document.category_config_uuid = "11111111-1111-4111-8111-111111111111"
            document.category_config_sha256 = "a" * 64
            repository.save(document)
            with image_path.with_suffix(".json").open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["format"], "parker-label-instance-v2")
            self.assertEqual(payload["category_config_uuid"], document.category_config_uuid)
            self.assertEqual(payload["category_config_sha256"], "a" * 64)
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
            document.add_segment(Category(1, "person", "person"), 100)
            mask = np.zeros((8, 10), dtype=np.uint8)
            mask[1:5, 1:5] = 1
            document.commit_mask(0, mask)
            repository = AnnotationRepository(target_size=10)
            document.category_config_uuid = "11111111-1111-4111-8111-111111111111"
            document.category_config_sha256 = "a" * 64
            repository.save(document)
            with image_path.with_suffix(".json").open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            self.assertEqual(payload["image"]["width"], 20)
            self.assertEqual(payload["image"]["height"], 16)
            self.assertEqual(payload["annotations"][0]["bbox"], [2, 2, 8, 8])
            self.assertEqual(payload["annotations"][0]["segmentation"]["size"], [16, 20])
            preview = cv2.imread(str(image_path.parent / "large.mask.png"), cv2.IMREAD_COLOR)
            self.assertEqual(preview.shape[:2], (16, 20))

if __name__ == "__main__":
    unittest.main()
