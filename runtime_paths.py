import json
import logging
import shutil
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt5.QtCore import QSettings


_SOURCE_ROOT = Path(__file__).resolve().parent
_LOGGER_NAME = "parker_label"


def resource_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return _SOURCE_ROOT


def program_directory():
    if not getattr(sys, "frozen", False):
        return _SOURCE_ROOT
    executable = Path(sys.executable).absolute()
    app_bundle = next((parent for parent in executable.parents if parent.suffix == ".app"), None)
    return app_bundle.parent if app_bundle else executable.parent


def config_directory():
    return program_directory() / "configs"


def portable_settings():
    return QSettings(str(config_directory() / "settings.ini"), QSettings.IniFormat)


def _migrate_settings(directory, original=None):
    original = original if original is not None else QSettings("ParkerLabel", "ParkerLabel")
    settings = portable_settings()
    keys = [key for key in original.allKeys() if not settings.contains(key)]
    if not keys:
        return
    for key in keys:
        settings.setValue(key, original.value(key))
    settings.sync()
    if settings.status() != QSettings.NoError:
        raise OSError(f"Cannot save portable settings: {directory / 'settings.ini'}")


def _migrate_categories(directory):
    if getattr(sys, "frozen", False):
        return
    original = _SOURCE_ROOT / "config" / "category-configs"
    if not original.is_dir():
        return
    for source in original.glob("*.json"):
        if source.name == "settings.json":
            settings = portable_settings()
            if not settings.contains("categories/default_config_uuid"):
                try:
                    value = json.loads(source.read_text(encoding="utf-8"))["default_config_uuid"]
                except (OSError, ValueError, KeyError, TypeError):
                    continue
                if isinstance(value, str):
                    settings.setValue("categories/default_config_uuid", value)
                    settings.sync()
                    if settings.status() != QSettings.NoError:
                        raise OSError(f"Cannot save portable settings: {settings.fileName()}")
            continue
        target = directory / "categories" / source.name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def prepare_runtime():
    directory = config_directory()
    (directory / "categories").mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    log_path = directory / "app.log"
    for path in (log_path, directory / "app.log.1"):
        path.unlink(missing_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    marker = directory / ".legacy-migration-complete"
    if not marker.exists():
        _migrate_settings(directory)
        _migrate_categories(directory)
        marker.touch()
    return directory
