import logging
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
    directory = config_directory()
    (directory / "categories").mkdir(parents=True, exist_ok=True)
    if getattr(sys, "frozen", False):
        model_directory().mkdir(parents=True, exist_ok=True)
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

    return directory
