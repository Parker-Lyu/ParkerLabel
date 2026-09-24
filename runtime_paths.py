import errno
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt5.QtCore import QSettings


_SOURCE_ROOT = Path(__file__).resolve().parent
_LOGGER_NAME = "parker_label"
_runtime_config_directory = None


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
    if _runtime_config_directory is not None:
        return _runtime_config_directory
    portable = program_directory() / "configs"
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        support = _macos_support_directory()
        if "AppTranslocation" in Path(sys.executable).parts or (
            support.exists() and not portable.exists()
        ):
            return support
    return portable


def _macos_support_directory():
    return Path.home() / "Library" / "Application Support" / "ParkerLabel" / "configs"


def model_directory():
    if getattr(sys, "frozen", False):
        return config_directory() / "pretrain"
    return _SOURCE_ROOT / "pretrain"


def model_manifest_path():
    return resource_root() / "model-bundle.json"


def application_icon_path():
    return resource_root() / "parker_label_app" / "assets" / "app-icon.png"


def portable_settings():
    return QSettings(str(config_directory() / "settings.ini"), QSettings.IniFormat)


def prepare_runtime():
    global _runtime_config_directory
    directory = config_directory()
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    try:
        _prepare_config_directory(directory, logger)
    except OSError as error:
        if (
            sys.platform != "darwin"
            or not getattr(sys, "frozen", False)
            or directory == _macos_support_directory()
            or error.errno not in (errno.EROFS, errno.EACCES, errno.EPERM)
        ):
            raise
        directory = _macos_support_directory()
        _prepare_config_directory(directory, logger)
    _runtime_config_directory = directory
    return directory


def _prepare_config_directory(directory, logger):
    (directory / "categories").mkdir(parents=True, exist_ok=True)
    if getattr(sys, "frozen", False):
        (directory / "pretrain").mkdir(parents=True, exist_ok=True)
    log_path = directory / "app.log"
    for path in (log_path, directory / "app.log.1"):
        path.unlink(missing_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
