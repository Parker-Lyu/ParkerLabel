import os
import threading
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtTest import QSignalSpy

from parker_label_app.update_checker import (
    GITEE_RELEASES_API,
    GITHUB_RELEASES_API,
    UpdateChecker,
    check_for_updates,
    parse_version,
    select_latest_release,
)


class UpdateLogicTests(unittest.TestCase):
    def test_semantic_version_comparison_uses_numeric_parts(self):
        self.assertGreater(parse_version("0.10.0"), parse_version("0.9.0"))
        self.assertEqual(parse_version("v1.2.3"), (1, 2, 3))
        with self.assertRaises(ValueError):
            parse_version(None)

    def test_release_filter_excludes_models_drafts_and_prereleases(self):
        release = select_latest_release(
            [
                {"tag_name": "models-v1", "body": "model"},
                {"tag_name": "v9.0.0", "draft": True},
                {"tag_name": "v8.0.0", "prerelease": True},
                {"tag_name": "v0.9.0", "body": "old"},
                {"tag_name": "v0.10.0", "body": "new"},
            ],
            "github",
        )
        self.assertEqual(release.version, "0.10.0")
        self.assertEqual(release.notes, "new")

    def test_github_failure_falls_back_to_gitee(self):
        calls = []
        statuses = []

        def fetcher(url, timeout):
            calls.append((url, timeout))
            if url == GITHUB_RELEASES_API:
                raise OSError("github unavailable")
            return [{"tag_name": "v0.10.0", "description": "release notes"}]

        result = check_for_updates("0.9.0", statuses.append, fetcher)

        self.assertEqual(
            [url for url, _timeout in calls],
            [GITHUB_RELEASES_API, GITEE_RELEASES_API],
        )
        self.assertEqual(statuses, ["github", "gitee"])
        self.assertTrue(result.update_available)
        self.assertEqual(result.release.source, "gitee")

    def test_successful_github_result_does_not_query_gitee(self):
        calls = []

        def fetcher(url, timeout):
            calls.append(url)
            return [{"tag_name": "v0.9.0"}]

        result = check_for_updates("0.9.0", fetcher=fetcher)

        self.assertEqual(calls, [GITHUB_RELEASES_API])
        self.assertFalse(result.update_available)

    def test_two_network_failures_raise_instead_of_reporting_latest(self):
        def fetcher(url, timeout):
            raise OSError(f"offline: {url}")

        with self.assertRaisesRegex(RuntimeError, "github:.*gitee:"):
            check_for_updates("0.9.0", fetcher=fetcher)


class UpdateCheckerThreadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_repeated_start_is_rejected_while_request_is_running(self):
        entered = threading.Event()
        release = threading.Event()

        def check_function(current_version, status_callback):
            entered.set()
            release.wait(2)
            raise OSError("stopped")

        checker = UpdateChecker("0.1.0", check_function)
        failed_spy = QSignalSpy(checker.failed)
        self.assertTrue(checker.start())
        self.assertTrue(entered.wait(1))
        self.assertFalse(checker.start())
        release.set()
        self.assertTrue(failed_spy.wait(1000))


if __name__ == "__main__":
    unittest.main()
