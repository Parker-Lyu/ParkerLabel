import json
import re
import threading
from dataclasses import dataclass
from urllib.request import Request, urlopen

from PyQt5.QtCore import QObject, pyqtSignal


GITHUB_RELEASES_API = (
    "https://api.github.com/repos/Parker-Lyu/ParkerLabel/releases?per_page=100"
)
GITEE_RELEASES_API = (
    "https://gitee.com/api/v5/repos/Parker-Lyu/ParkerLabel/releases"
    "?page=1&per_page=100&direction=desc"
)
REQUEST_TIMEOUT = 8
VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    version_parts: tuple
    notes: str
    source: str


@dataclass(frozen=True)
class UpdateResult:
    current_version: str
    release: ReleaseInfo | None
    source: str

    @property
    def update_available(self):
        return self.release is not None and self.release.version_parts > parse_version(
            self.current_version
        )


def parse_version(value):
    match = VERSION_PATTERN.fullmatch(str(value or "").strip())
    if match is None:
        raise ValueError(f"Invalid application version: {value or 'unset'}")
    return tuple(int(part) for part in match.groups())


def select_latest_release(releases, source):
    candidates = []
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name") or "").strip()
        if tag.lower().startswith("models-"):
            continue
        try:
            version_parts = parse_version(tag)
        except ValueError:
            continue
        candidates.append(
            ReleaseInfo(
                version=".".join(str(part) for part in version_parts),
                version_parts=version_parts,
                notes=str(release.get("body") or release.get("description") or "").strip(),
                source=source,
            )
        )
    return max(candidates, key=lambda item: item.version_parts, default=None)


def fetch_releases(url, timeout=REQUEST_TIMEOUT):
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ParkerLabel-Update-Checker",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("Release response is not a list")
    return data


def check_for_updates(current_version, status_callback=None, fetcher=fetch_releases):
    parse_version(current_version)
    errors = []
    sources = (
        ("github", GITHUB_RELEASES_API),
        ("gitee", GITEE_RELEASES_API),
    )
    for source, url in sources:
        if status_callback is not None:
            status_callback(source)
        try:
            releases = fetcher(url, timeout=REQUEST_TIMEOUT)
            latest = select_latest_release(releases, source)
            return UpdateResult(str(current_version), latest, source)
        except Exception as error:
            errors.append(f"{source}: {error}")
    raise RuntimeError("; ".join(errors))


class UpdateChecker(QObject):
    checking = pyqtSignal(str)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, current_version, check_function=check_for_updates):
        super().__init__()
        self.current_version = current_version
        self.check_function = check_function
        self._lock = threading.Lock()
        self._running = False

    @property
    def running(self):
        with self._lock:
            return self._running

    def start(self):
        with self._lock:
            if self._running:
                return False
            self._running = True
        threading.Thread(target=self._run, daemon=True).start()
        return True

    def _run(self):
        try:
            result = self.check_function(self.current_version, self.checking.emit)
        except Exception as error:
            self.failed.emit(str(error))
        else:
            self.completed.emit(result)
        finally:
            with self._lock:
                self._running = False
