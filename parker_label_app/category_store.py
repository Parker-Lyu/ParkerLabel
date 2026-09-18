import hashlib
import json
import os
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from .models import Category


class CategoryConfigError(ValueError):
    pass


def _write_json(path, payload, overwrite=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not overwrite and path.exists():
        raise CategoryConfigError(f"配置名称重复：{path.stem}")
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        if overwrite:
            os.replace(temporary_path, path)
        else:
            try:
                os.link(temporary_path, path)
            except FileExistsError as error:
                raise CategoryConfigError(f"配置名称重复：{path.stem}") from error
            os.unlink(temporary_path)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise


def _canonical_uuid(value):
    if not isinstance(value, str):
        raise CategoryConfigError("类别配置 uuid 必须是字符串")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as error:
        raise CategoryConfigError(f"类别配置 uuid 无效：{value}") from error
    canonical = str(parsed)
    if value != canonical:
        raise CategoryConfigError(f"类别配置 uuid 必须使用标准格式：{canonical}")
    return canonical


def _content_hash(payload):
    content = {key: value for key, value in payload.items() if key != "sha256"}
    encoded = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _created_at(value):
    if not isinstance(value, str):
        raise CategoryConfigError("类别配置 created_at 必须是字符串")
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise CategoryConfigError(f"类别配置 created_at 无效：{value}") from error
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise CategoryConfigError("类别配置 created_at 必须包含时区")
    return value


@dataclass(frozen=True)
class CategoryConfigData:
    uuid: str
    created_at: str
    categories: tuple[Category, ...]
    content_hash: str


class CategoryStore:
    FIELDS = {"id", "name", "supercategory", "description", "enabled"}
    TOP_LEVEL_FIELDS = {
        "schema_version",
        "uuid",
        "created_at",
        "sha256",
        "preset",
        "categories",
    }
    SCHEMA_VERSION = 4

    def __init__(self, path: Path, readonly=False):
        """Initialize a category store backed by one local JSON file."""
        self.path = Path(path)
        self.readonly = readonly

    def load_data(self):
        """Load and validate a complete category configuration."""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError) as error:
            raise CategoryConfigError(f"无法读取类别配置：{error}") from error
        if not isinstance(payload, dict):
            raise CategoryConfigError("类别配置必须是 JSON 对象")
        extra = sorted(set(payload) - self.TOP_LEVEL_FIELDS)
        if extra:
            raise CategoryConfigError(f"类别配置包含未知字段：{', '.join(extra)}")
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise CategoryConfigError(
                f"不支持的类别配置版本：{payload.get('schema_version')}"
            )
        config_uuid = _canonical_uuid(payload.get("uuid"))
        created_at = _created_at(payload.get("created_at"))
        raw_categories = payload.get("categories")
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
                raise CategoryConfigError(
                    f"第 {row} 条类别字段无效（{'；'.join(details)}）"
                )
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
        content_hash = _content_hash(payload)
        sha256 = payload.get("sha256")
        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or any(character not in "0123456789abcdef" for character in sha256)
        ):
            raise CategoryConfigError("类别配置 sha256 无效")
        if sha256 != content_hash:
            raise CategoryConfigError("类别配置 sha256 校验失败")
        return CategoryConfigData(
            config_uuid,
            created_at,
            tuple(categories),
            content_hash,
        )

    def load(self):
        """Load validated categories from local JSON."""
        return list(self.load_data().categories)

    def save(self, config_uuid, created_at, categories, overwrite=False):
        """Validate and atomically save a category configuration."""
        if self.readonly:
            raise CategoryConfigError("已有类别配置不可修改")
        config_uuid = _canonical_uuid(config_uuid)
        created_at = _created_at(created_at)
        categories = list(categories)
        self.validate(categories)
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "uuid": config_uuid,
            "created_at": created_at,
            "categories": [category.to_dict() for category in categories],
        }
        payload["sha256"] = _content_hash(payload)
        _write_json(self.path, payload, overwrite=overwrite)

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


@dataclass(frozen=True)
class CategoryConfig:
    id: str
    name: str
    created_at: str
    content_hash: str
    builtin: bool = False


class CategoryConfigManager:
    BUILTIN_ID = "c2da0de2-f465-4109-98f1-08a5bd881803"
    BUILTIN_NAME = "COCO 默认"
    SETTINGS_NAME = "settings.json"

    def __init__(self, builtin_path, user_directory=None):
        """Manage the built-in category set and immutable user configurations."""
        self.builtin_store = CategoryStore(builtin_path, readonly=True)
        if user_directory is None:
            user_directory = Path(builtin_path).parent / "category-configs"
        self.user_directory = Path(user_directory)
        self.settings_path = self.user_directory / self.SETTINGS_NAME
        self.warning = ""
        self._drafts = {}
        if self.builtin_store.load_data().uuid != self.BUILTIN_ID:
            raise CategoryConfigError("内置 COCO 配置 uuid 与程序不一致")

    def new_uuid(self):
        """Return a new configuration identifier."""
        return str(uuid4())

    def _config_path(self, name):
        return self.user_directory / f"{name}.json"

    def _validate_filename(self, name):
        name = unicodedata.normalize("NFC", name.strip())
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
            return self.BUILTIN_ID
        try:
            with self.settings_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if set(payload) != {"default_config_uuid"}:
                raise ValueError("设置字段无效")
            return _canonical_uuid(payload["default_config_uuid"])
        except (OSError, json.JSONDecodeError, ValueError, CategoryConfigError) as error:
            self.warning = f"类别配置设置无效，已回退到内置 COCO：{error}"
            return self.BUILTIN_ID

    def _write_settings(self, config_id):
        _write_json(self.settings_path, {"default_config_uuid": config_id})

    def configurations(self):
        """Return validated configurations and reject duplicate UUID values."""
        builtin_data = self.builtin_store.load_data()
        result = [
            CategoryConfig(
                builtin_data.uuid,
                self.BUILTIN_NAME,
                builtin_data.created_at,
                builtin_data.content_hash,
                True,
            )
        ]
        if self.user_directory.exists():
            paths = sorted(
                (
                    path
                    for path in self.user_directory.glob("*.json")
                    if path.name not in {self.SETTINGS_NAME, "index.json"}
                ),
                key=lambda path: path.stem.casefold(),
            )
            for path in paths:
                data = CategoryStore(path, readonly=True).load_data()
                result.append(
                    CategoryConfig(
                        data.uuid,
                        path.stem,
                        data.created_at,
                        data.content_hash,
                    )
                )
        duplicates = {
            config.id
            for config in result
            if sum(item.id == config.id for item in result) > 1
        }
        if duplicates:
            raise CategoryConfigError(
                f"类别配置 uuid 重复：{', '.join(sorted(duplicates))}"
            )
        return result

    def configuration(self, config_id):
        """Return one configuration descriptor by UUID."""
        for config in self.configurations():
            if config.id == config_id:
                return config
        raise CategoryConfigError(f"找不到类别配置：{config_id}")

    def load_data(self, config_id):
        """Load one built-in or user category configuration by UUID."""
        config = self.configuration(config_id)
        store = self.builtin_store if config.builtin else CategoryStore(
            self._config_path(config.name), readonly=True
        )
        return store.load_data()

    def load(self, config_id):
        """Load categories from one configuration by UUID."""
        return list(self.load_data(config_id).categories)

    def default_config_id(self):
        """Return the saved startup default when it still exists."""
        config_id = self._read_settings()
        try:
            self.configuration(config_id)
            return config_id
        except CategoryConfigError:
            self.warning = "启动默认类别配置不存在，已回退到内置 COCO"
            return self.BUILTIN_ID

    def load_default(self):
        """Load the startup default and safely fall back to the built-in set."""
        config_id = self.default_config_id()
        try:
            return config_id, self.load_data(config_id)
        except CategoryConfigError as error:
            self.warning = f"启动默认类别配置无效，已回退到内置 COCO：{error}"
            return self.BUILTIN_ID, self.load_data(self.BUILTIN_ID)

    def _validate_name(self, name):
        name = self._validate_filename(name)
        for config in self.configurations():
            if unicodedata.normalize("NFC", config.name).casefold() == name.casefold():
                raise CategoryConfigError(f"配置名称重复：{name}")
        return name

    def create(self, name, config_uuid, categories):
        """Create a new editable draft without overwriting existing files."""
        name = self._validate_name(name)
        config_uuid = _canonical_uuid(config_uuid)
        try:
            self.configuration(config_uuid)
        except CategoryConfigError:
            pass
        else:
            raise CategoryConfigError(f"类别配置 uuid 重复：{config_uuid}")
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        CategoryStore(self._config_path(name)).save(
            config_uuid, created_at, categories
        )
        self._drafts[config_uuid] = name
        return config_uuid

    def save_draft(self, config_id, categories):
        """Save a configuration created by the current editor session."""
        name = self._drafts.get(config_id)
        if name is None:
            raise CategoryConfigError("已有类别配置不可修改，请复制后编辑")
        data = CategoryStore(self._config_path(name), readonly=True).load_data()
        if data.uuid != config_id:
            raise CategoryConfigError("草稿配置 uuid 与文件不一致")
        CategoryStore(self._config_path(name)).save(
            config_id,
            data.created_at,
            categories,
            overwrite=True,
        )

    def freeze(self, config_id):
        """Make a saved draft immutable."""
        self._drafts.pop(config_id, None)

    def set_default(self, config_id):
        """Set the configuration loaded at application startup."""
        self.configuration(config_id)
        self._write_settings(config_id)
