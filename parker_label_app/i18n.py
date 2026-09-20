import json
from string import Formatter

from PyQt5.QtCore import QObject, pyqtSignal

from runtime_paths import portable_settings, resource_root


LANGUAGE_NAMES = {
    "zh_CN": "中文（简体）",
    "zh_TW": "中文（繁體）",
    "en_US": "English",
    "ja_JP": "日本語",
    "ko_KR": "한국어",
    "de_DE": "Deutsch",
    "fr_FR": "Français",
    "it_IT": "Italiano",
    "es_ES": "Español",
}


_TEXT = {}


_LOCALE_DIR = resource_root() / "parker_label_app" / "locales"
_FORMATTER = Formatter()
for _code in LANGUAGE_NAMES:
    with (_LOCALE_DIR / f"{_code}.json").open(encoding="utf-8") as _file:
        _TEXT[_code] = json.load(_file)
    if _TEXT[_code].keys() != _TEXT["zh_CN"].keys():
        raise ValueError(f"Incomplete translations: {_code}")
    for _key, _template in _TEXT[_code].items():
        _fields = {
            (name, format_spec)
            for _, name, format_spec, _ in _FORMATTER.parse(_template)
            if name
        }
        _expected = {
            (name, format_spec)
            for _, name, format_spec, _ in _FORMATTER.parse(_TEXT["zh_CN"][_key])
            if name
        }
        if _fields != _expected:
            raise ValueError(f"Invalid translation placeholders: {_code}.{_key}")


class LanguageManager(QObject):
    languageChanged = pyqtSignal(str)

    def __init__(self, settings=None):
        """Load and persist the selected interface language."""
        super().__init__()
        self.settings = settings if settings is not None else portable_settings()
        language = self.settings.value("interface/language", "zh_CN", type=str)
        self._language = language if language in _TEXT else "zh_CN"

    @property
    def language(self):
        """Return the active language code."""
        return self._language

    def set_language(self, language):
        """Persist and publish a supported language change."""
        if language not in _TEXT:
            raise ValueError(f"Unsupported language: {language}")
        if language == self._language:
            return
        self._language = language
        self.settings.setValue("interface/language", language)
        self.settings.sync()
        self.languageChanged.emit(language)

    def text(self, key, **values):
        """Return formatted interface text for the active language."""
        template = _TEXT[self._language].get(key, key)
        return template.format(**values)


language_manager = LanguageManager()
