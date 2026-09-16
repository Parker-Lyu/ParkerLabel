import json
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from PyQt5.QtCore import QStandardPaths

from .models import Category


class CategoryConfigError(ValueError):
    pass


def _write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary_path, path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


class CategoryStore:
    FIELDS = {"id", "name", "supercategory", "description", "enabled"}

    def __init__(self, path: Path, readonly=False):
        """Initialize a category store backed by one local JSON file."""
        self.path = Path(path)
        self.readonly = readonly

    def load(self):
        """Load and validate categories from local JSON."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise CategoryConfigError(f"无法读取类别配置：{error}") from error
        raw_categories = payload.get("categories") if isinstance(payload, dict) else payload
        if not isinstance(raw_categories, list):
            raise CategoryConfigError("类别配置必须包含 categories 数组")
        categories = []
        for row, value in enumerate(raw_categories, 1):
            if not isinstance(value, dict):
                raise CategoryConfigError(f"第 {row} 条类别必须是对象")
            fields = set(value)
            if fields != self.FIELDS:
                missing = sorted(self.FIELDS - fields)
                extra = sorted(fields - self.FIELDS)
                details = []
                if missing:
                    details.append(f"缺少字段：{', '.join(missing)}")
                if extra:
                    details.append(f"未知字段：{', '.join(extra)}")
                detail = "；".join(details)
                raise CategoryConfigError(f"第 {row} 条类别字段无效（{detail}）")
            if isinstance(value["id"], bool) or not isinstance(value["id"], int):
                raise CategoryConfigError(f"第 {row} 条类别 ID 必须是整数")
            if not isinstance(value["enabled"], bool):
                raise CategoryConfigError(f"第 {row} 条类别 enabled 必须是布尔值")
            if not all(
                isinstance(value[field], str)
                for field in ("name", "supercategory", "description")
            ):
                raise CategoryConfigError(f"第 {row} 条类别文本字段必须是字符串")
            categories.append(Category.from_dict(value))
        self.validate(categories)
        return categories

    def save(self, categories):
        """Validate and atomically save categories to local JSON."""
        if self.readonly:
            raise CategoryConfigError("内置类别配置不可覆盖")
        categories = list(categories)
        self.validate(categories)
        _write_json(
            self.path,
            {
                "schema_version": 1,
                "categories": [category.to_dict() for category in categories],
            },
        )

    @staticmethod
    def validate(categories):
        """Reject incomplete, duplicate, or out-of-range category values."""
        if not categories:
            raise CategoryConfigError("至少需要一个类别条目")
        ids = set()
        names = set()
        for category in categories:
            if (
                isinstance(category.id, bool)
                or not isinstance(category.id, int)
                or category.id <= 0
            ):
                raise CategoryConfigError("类别 ID 必须是正整数")
            if not all(
                isinstance(value, str)
                for value in (category.name, category.supercategory, category.description)
            ):
                raise CategoryConfigError("类别文本字段必须是字符串")
            if not isinstance(category.enabled, bool):
                raise CategoryConfigError("类别 enabled 必须是布尔值")
            if not category.name:
                raise CategoryConfigError("类别名称不能为空")
            normalized_name = category.name.casefold()
            if category.id in ids:
                raise CategoryConfigError(f"类别 ID 重复：{category.id}")
            if normalized_name in names:
                raise CategoryConfigError(f"类别名称重复：{category.name}")
            ids.add(category.id)
            names.add(normalized_name)

    def enabled(self):
        """Return enabled categories in stored order."""
        return [category for category in self.load() if category.enabled]

    def by_name(self):
        """Return enabled categories keyed by exact name."""
        return {category.name: category for category in self.enabled()}


@dataclass(frozen=True)
class CategoryConfig:
    id: str
    name: str
    builtin: bool = False


class CategoryConfigManager:
    BUILTIN_ID = "builtin-coco"
    BUILTIN_NAME = "COCO 默认"

    def __init__(self, builtin_path, user_directory=None):
        """Manage the built-in category set and named user configurations."""
        self.builtin_store = CategoryStore(builtin_path, readonly=True)
        if user_directory is None:
            user_directory = Path(builtin_path).parent / "category-configs"
            legacy_base = Path(
                QStandardPaths.writableLocation(QStandardPaths.AppConfigLocation)
            )
            legacy_directory = legacy_base / "category-configs"
        else:
            legacy_directory = None
        self.user_directory = Path(user_directory)
        self.config_directory = self.user_directory / "configs"
        self.index_path = self.user_directory / "index.json"
        self.warning = ""
        self._migrate_legacy_directory(legacy_directory)

    def _migrate_legacy_directory(self, legacy_directory):
        """Copy legacy system-level configurations into the project config directory."""
        if legacy_directory is None or self.index_path.exists():
            return
        legacy_directory = Path(legacy_directory)
        if not (legacy_directory / "index.json").exists():
            return
        try:
            shutil.copytree(legacy_directory, self.user_directory)
            self.warning = f"用户类别配置已迁移至 {self.user_directory}"
        except OSError as error:
            self.warning = f"迁移用户类别配置失败：{error}"

    @staticmethod
    def _empty_index():
        return {
            "schema_version": 1,
            "default_config_id": CategoryConfigManager.BUILTIN_ID,
            "configs": [],
        }

    def _read_index(self):
        if not self.index_path.exists():
            return self._empty_index()
        try:
            with self.index_path.open("r", encoding="utf-8") as handle:
                index = json.load(handle)
            if not isinstance(index, dict) or index.get("schema_version") != 1:
                raise ValueError("不支持的索引格式")
            if not isinstance(index.get("configs"), list):
                raise ValueError("configs 必须是数组")
            if not isinstance(index.get("default_config_id"), str):
                raise ValueError("default_config_id 必须是字符串")
            ids = set()
            names = set()
            for value in index["configs"]:
                if set(value) != {"id", "name", "file"}:
                    raise ValueError("配置索引字段无效")
                if not all(isinstance(value[key], str) and value[key] for key in value):
                    raise ValueError("配置索引值无效")
                if Path(value["file"]).name != value["file"]:
                    raise ValueError("配置文件名无效")
                normalized_name = value["name"].casefold()
                if value["id"] in ids or normalized_name in names:
                    raise ValueError("配置索引包含重复项")
                ids.add(value["id"])
                names.add(normalized_name)
            return index
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.warning = f"用户类别配置索引无效，已回退到内置 COCO：{error}"
            return self._empty_index()

    def _write_index(self, index):
        _write_json(self.index_path, index)

    def configurations(self):
        """Return the built-in configuration followed by named user configurations."""
        result = [CategoryConfig(self.BUILTIN_ID, self.BUILTIN_NAME, True)]
        result.extend(
            CategoryConfig(value["id"], value["name"])
            for value in self._read_index()["configs"]
        )
        return result

    def configuration(self, config_id):
        """Return one configuration descriptor."""
        for config in self.configurations():
            if config.id == config_id:
                return config
        raise CategoryConfigError("类别配置不存在")

    @staticmethod
    def _entry(index, config_id):
        for value in index["configs"]:
            if value["id"] == config_id:
                return value
        raise CategoryConfigError("类别配置不存在")

    def _path(self, entry):
        return self.config_directory / entry["file"]

    def load(self, config_id):
        """Load one built-in or user category configuration."""
        if config_id == self.BUILTIN_ID:
            return self.builtin_store.load()
        index = self._read_index()
        return CategoryStore(self._path(self._entry(index, config_id))).load()

    def default_config_id(self):
        """Return the saved startup default when it still exists."""
        index = self._read_index()
        config_id = index.get("default_config_id", self.BUILTIN_ID)
        if config_id == self.BUILTIN_ID:
            return config_id
        if any(value["id"] == config_id for value in index["configs"]):
            return config_id
        self.warning = "启动默认类别配置不存在，已回退到内置 COCO"
        return self.BUILTIN_ID

    def load_default(self):
        """Load the startup default and safely fall back to the built-in set."""
        config_id = self.default_config_id()
        try:
            return config_id, self.load(config_id)
        except CategoryConfigError as error:
            self.warning = f"启动默认类别配置无效，已回退到内置 COCO：{error}"
            return self.BUILTIN_ID, self.load(self.BUILTIN_ID)

    def _validate_name(self, name, excluding_id=None):
        name = name.strip()
        if not name:
            raise CategoryConfigError("配置名称不能为空")
        if name.casefold() == self.BUILTIN_NAME.casefold():
            raise CategoryConfigError("该名称由内置配置保留")
        for config in self.configurations():
            if config.id != excluding_id and config.name.casefold() == name.casefold():
                raise CategoryConfigError(f"配置名称重复：{name}")
        return name

    def create(self, name, categories):
        """Create and return a named user configuration."""
        name = self._validate_name(name)
        categories = list(categories)
        CategoryStore.validate(categories)
        index = self._read_index()
        config_id = uuid.uuid4().hex
        filename = f"{config_id}.json"
        path = self.config_directory / filename
        CategoryStore(path).save(categories)
        index["configs"].append({"id": config_id, "name": name, "file": filename})
        try:
            self._write_index(index)
        except Exception:
            try:
                path.unlink()
            except OSError:
                pass
            raise
        return config_id

    def save(self, config_id, categories):
        """Overwrite one user configuration."""
        if config_id == self.BUILTIN_ID:
            raise CategoryConfigError("内置类别配置不可覆盖，请另存为用户配置")
        index = self._read_index()
        CategoryStore(self._path(self._entry(index, config_id))).save(categories)

    def rename(self, config_id, name):
        """Rename one user configuration."""
        if config_id == self.BUILTIN_ID:
            raise CategoryConfigError("内置类别配置不可重命名")
        name = self._validate_name(name, excluding_id=config_id)
        index = self._read_index()
        self._entry(index, config_id)["name"] = name
        self._write_index(index)

    def set_default(self, config_id):
        """Set the configuration loaded at application startup."""
        self.configuration(config_id)
        index = self._read_index()
        index["default_config_id"] = config_id
        self._write_index(index)

    def delete(self, config_id):
        """Delete one user configuration and repair the startup default."""
        if config_id == self.BUILTIN_ID:
            raise CategoryConfigError("内置类别配置不可删除")
        index = self._read_index()
        entry = self._entry(index, config_id)
        index["configs"].remove(entry)
        if index.get("default_config_id") == config_id:
            index["default_config_id"] = self.BUILTIN_ID
        self._write_index(index)
        try:
            self._path(entry).unlink()
        except FileNotFoundError:
            pass
