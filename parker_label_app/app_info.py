APP_NAME = "ParkerLabel"
APP_VERSION = None
APP_DEVELOPER = "Parker Lyu"
REPOSITORY_URL = "https://github.com/Parker-Lyu/ParkerLabel"
GITEE_REPOSITORY_URL = "https://gitee.com/Parker-Lyu/ParkerLabel"
CHANGELOG_URL = f"{REPOSITORY_URL}/blob/main/CHANGELOG.md"
GITHUB_RELEASES_URL = f"{REPOSITORY_URL}/releases"
GITEE_RELEASES_URL = f"{GITEE_REPOSITORY_URL}/releases"


def source_code_url(version=APP_VERSION):
    ref = f"v{version}" if version else "main"
    return f"{REPOSITORY_URL}/tree/{ref}"
