import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

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
    BUILTIN_FILE = "../default-coco.json"
    SETTINGS_NAME = "settings.json"

    def __init__(self, builtin_path, user_directory=None):
        """Manage the built-in category set and named user configurations."""
        self.builtin_store = CategoryStore(builtin_path, readonly=True)
        if user_directory is None:
            user_directory = Path(builtin_path).parent / "category-configs"
        self.user_directory = Path(user_directory)
        self.settings_path = self.user_directory / self.SETTINGS_NAME
        self.warning = ""

    def _config_path(self, name):
        return self.user_directory / f"{name}.json"

    def _validate_filename(self, name):
        name = name.strip()
        if not name:
            raise CategoryConfigError("配置名称不能为空")
        if name.casefold() == self.BUILTIN_NAME.casefold():
            raise CategoryConfigError("该名称由内置配置保留")
        if name.casefold() in {"settings", "index"}:
            raise CategoryConfigError("该名称由程序保留")
        if name in {".", ".."} or name.startswith("."):
            raise CategoryConfigError("配置名称不能以点开头")
        if name.endswith(".") or name.casefold().endswith(".json"):
            raise CategoryConfigError("配置名称不能以点或 .json 结尾")
        if any(character in name for character in '<>:"/\\|?*\0'):
            raise CategoryConfigError("配置名称包含文件名非法字符")
        if any(ord(character) < 32 for character in name):
            raise CategoryConfigError("配置名称不能包含控制字符")
        return name

    def _read_settings(self):
        if not self.settings_path.exists():
            return self.BUILTIN_FILE
        try:
            with self.settings_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if set(payload) != {"default_config_file"}:
                raise ValueError("设置字段无效")
            filename = payload["default_config_file"]
            if not isinstance(filename, str) or not filename:
                raise ValueError("default_config_file 必须是字符串")
            return filename
        except (OSError, json.JSONDecodeError, ValueError) as error:
            self.warning = f"类别配置设置无效，已回退到内置 COCO：{error}"
            return self.BUILTIN_FILE

    def _write_settings(self, config_id):
        filename = (
            self.BUILTIN_FILE
            if config_id == self.BUILTIN_ID
            else f"{config_id}.json"
        )
        _write_json(self.settings_path, {"default_config_file": filename})

    def configurations(self):
        """Return the built-in configuration followed by named JSON files."""
        result = [CategoryConfig(self.BUILTIN_ID, self.BUILTIN_NAME, True)]
        if not self.user_directory.exists():
            return result
        paths = sorted(
            (
                path
                for path in self.user_directory.glob("*.json")
                if path.name not in {self.SETTINGS_NAME, "index.json"}
            ),
            key=lambda path: path.stem.casefold(),
        )
        result.extend(CategoryConfig(path.stem, path.stem) for path in paths)
        return result

    def configuration(self, config_id):
        """Return one configuration descriptor."""
        for config in self.configurations():
            if config.id == config_id:
                return config
        raise CategoryConfigError("类别配置不存在")

    def load(self, config_id):
        """Load one built-in or user category configuration."""
        if config_id == self.BUILTIN_ID:
            return self.builtin_store.load()
        self.configuration(config_id)
        return CategoryStore(self._config_path(config_id)).load()

    def default_config_id(self):
        """Return the saved startup default when it still exists."""
        filename = self._read_settings()
        if filename == self.BUILTIN_FILE:
            return self.BUILTIN_ID
        path = Path(filename)
        if path.name == filename and path.suffix == ".json":
            config_id = path.stem
            if self._config_path(config_id).is_file():
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
        name = self._validate_filename(name)
        for config in self.configurations():
            if config.id != excluding_id and config.name.casefold() == name.casefold():
                raise CategoryConfigError(f"配置名称重复：{name}")
        return name

    def create(self, name, categories):
        """Create and return a user configuration named by its JSON file."""
        name = self._validate_name(name)
        CategoryStore(self._config_path(name)).save(categories)
        return name

    def save(self, config_id, categories):
        """Overwrite one user configuration."""
        if config_id == self.BUILTIN_ID:
            raise CategoryConfigError("内置类别配置不可覆盖，请另存为用户配置")
        self.configuration(config_id)
        CategoryStore(self._config_path(config_id)).save(categories)

    def rename(self, config_id, name):
        """Rename one user configuration and its JSON file."""
        if config_id == self.BUILTIN_ID:
            raise CategoryConfigError("内置类别配置不可重命名")
        self.configuration(config_id)
        name = self._validate_name(name, excluding_id=config_id)
        old_path = self._config_path(config_id)
        new_path = self._config_path(name)
        old_path.rename(new_path)
        if self._read_settings() == f"{config_id}.json":
            try:
                self._write_settings(name)
            except Exception:
                new_path.rename(old_path)
                raise
        return name

    def set_default(self, config_id):
        """Set the configuration loaded at application startup."""
        self.configuration(config_id)
        self._write_settings(config_id)

    def delete(self, config_id):
        """Delete one user configuration and repair the startup default."""
        if config_id == self.BUILTIN_ID:
            raise CategoryConfigError("内置类别配置不可删除")
        self.configuration(config_id)
        if self._read_settings() == f"{config_id}.json":
            self._write_settings(self.BUILTIN_ID)
        try:
            self._config_path(config_id).unlink()
        except FileNotFoundError:
            pass
