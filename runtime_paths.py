import ctypes
import errno
import os
import logging
import sys
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PyQt5.QtCore import QSettings


_SOURCE_ROOT = Path(__file__).resolve().parent
_LOGGER_NAME = "parker_label"


class PortableLocationError(OSError):
    def __init__(self, directory, translocated=False):
        self.directory = directory
        self.translocated = translocated
        super().__init__(f"Portable data directory is unavailable: {directory}")


def resource_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return _SOURCE_ROOT


def program_directory():
    if not getattr(sys, "frozen", False):
        return _SOURCE_ROOT
    executable = Path(sys.executable).absolute()
    app_bundle = next((parent for parent in executable.parents if parent.suffix == ".app"), None)
    if app_bundle and sys.platform == "darwin" and "AppTranslocation" in app_bundle.parts:
        app_bundle = _original_app_bundle(app_bundle) or app_bundle
    return app_bundle.parent if app_bundle else executable.parent


@lru_cache(maxsize=8)
def _original_app_bundle(bundle):
    try:
        core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        core.CFURLCreateFromFileSystemRepresentation.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool,
        ]
        core.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
        core.CFURLGetFileSystemRepresentation.argtypes = [
            ctypes.c_void_p, ctypes.c_bool, ctypes.c_void_p, ctypes.c_long,
        ]
        core.CFURLGetFileSystemRepresentation.restype = ctypes.c_bool
        core.CFRelease.argtypes = [ctypes.c_void_p]
        core.CFRelease.restype = None
        original_path = security.SecTranslocateCreateOriginalPathForURL
        original_path.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        original_path.restype = ctypes.c_void_p
        encoded = os.fsencode(bundle)
        source = core.CFURLCreateFromFileSystemRepresentation(None, encoded, len(encoded), True)
        if not source:
            return None
        original = None
        error = ctypes.c_void_p()
        try:
            original = original_path(source, ctypes.byref(error))
            if not original:
                return None
            buffer = ctypes.create_string_buffer(4096)
            if not core.CFURLGetFileSystemRepresentation(original, True, buffer, len(buffer)):
                return None
            path = Path(os.fsdecode(buffer.value))
            if (path.is_absolute() and path.name == bundle.name and path.is_dir()
                    and "AppTranslocation" not in path.parts):
                return path
        finally:
            if error.value:
                core.CFRelease(error)
            if original:
                core.CFRelease(original)
            core.CFRelease(source)
    except (OSError, AttributeError):
        return None
    return None


def config_directory():
    return program_directory() / "configs"


def model_directory():
    if getattr(sys, "frozen", False):
        return resource_root() / "pretrain"
    return _SOURCE_ROOT / "pretrain"


def model_manifest_path():
    return resource_root() / "model-bundle.json"


def application_icon_path():
    return resource_root() / "parker_label_app" / "assets" / "app-icon.png"


def portable_settings():
    return QSettings(str(config_directory() / "settings.ini"), QSettings.IniFormat)


def prepare_runtime():
    directory = config_directory()
    if (
        sys.platform == "darwin"
        and getattr(sys, "frozen", False)
        and "AppTranslocation" in directory.parts
    ):
        raise PortableLocationError(directory, translocated=True)
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    try:
        _prepare_config_directory(directory, logger)
    except OSError as error:
        if error.errno not in (errno.EROFS, errno.EACCES, errno.EPERM):
            raise
        raise PortableLocationError(directory) from error
    return directory


def _prepare_config_directory(directory, logger):
    (directory / "categories").mkdir(parents=True, exist_ok=True)
    log_path = directory / "app.log"
    for path in (log_path, directory / "app.log.1"):
        path.unlink(missing_ok=True)
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
