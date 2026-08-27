import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "updater"))

import updater


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.source = root / "source"
        self.app = root / "app"
        self.source.mkdir()
        self.app.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    @staticmethod
    def write(root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_collect_managed_files_excludes_local_data(self):
        self.write(self.source, "app.py", "new")
        self.write(self.source, ".env", "secret")
        self.write(self.source, "exports/result.xlsx", "generated")
        self.write(self.source, "endpoints/chrome_driver/chromedriver.exe", "binary")

        self.assertEqual(updater.collect_managed_files(self.source), ["app.py"])

    def test_synchronize_preserves_local_files_and_removes_obsolete(self):
        self.write(self.source, "app.py", "new")
        self.write(self.source, "new_module.py", "added")
        self.write(self.app, "app.py", "old")
        self.write(self.app, "obsolete.py", "remove")
        self.write(self.app, ".env", "keep-secret")
        self.write(self.app, "exports/report.xlsx", "keep-report")

        updater.synchronize_files(
            self.source,
            self.app,
            ["app.py", "new_module.py"],
            ["app.py", "obsolete.py"],
        )

        self.assertEqual((self.app / "app.py").read_text(encoding="utf-8"), "new")
        self.assertEqual((self.app / "new_module.py").read_text(encoding="utf-8"), "added")
        self.assertFalse((self.app / "obsolete.py").exists())
        self.assertEqual((self.app / ".env").read_text(encoding="utf-8"), "keep-secret")
        self.assertEqual(
            (self.app / "exports/report.xlsx").read_text(encoding="utf-8"), "keep-report"
        )

    def test_synchronize_rolls_back_after_copy_failure(self):
        self.write(self.source, "app.py", "new")
        self.write(self.source, "second.py", "new second")
        self.write(self.app, "app.py", "old")
        self.write(self.app, "obsolete.py", "old obsolete")

        def fail_on_second(operation: str, relative: str) -> None:
            if operation == "copy" and relative == "second.py":
                raise OSError("simulated failure")

        with self.assertRaises(OSError):
            updater.synchronize_files(
                self.source,
                self.app,
                ["app.py", "second.py"],
                ["app.py", "obsolete.py"],
                operation_hook=fail_on_second,
            )

        self.assertEqual((self.app / "app.py").read_text(encoding="utf-8"), "old")
        self.assertEqual(
            (self.app / "obsolete.py").read_text(encoding="utf-8"), "old obsolete"
        )
        self.assertFalse((self.app / "second.py").exists())

    def test_ssl_context_has_trusted_certificates(self):
        bundle = updater._certificate_bundle()
        if bundle is not None:
            self.assertTrue(Path(bundle).is_file())
        self.assertTrue(updater._ssl_context().get_ca_certs())

    def test_certificate_bundle_prefers_ssl_cert_file(self):
        custom = Path(self.temporary.name) / "custom-ca.pem"
        custom.write_text("", encoding="utf-8")
        previous = os.environ.get("SSL_CERT_FILE")
        os.environ["SSL_CERT_FILE"] = str(custom)
        try:
            self.assertEqual(updater._certificate_bundle(), str(custom))
        finally:
            if previous is None:
                del os.environ["SSL_CERT_FILE"]
            else:
                os.environ["SSL_CERT_FILE"] = previous

    def test_env_file_with_credentials_is_renamed(self):
        self.write(self.app, "env", "GENBA_USERNAME=tizio\nGENBA_PASSWORD=segreto\n")

        updater.resolve_env_name_conflict(self.app, lambda message: None)

        self.assertFalse((self.app / "env").exists())
        self.assertIn("GENBA_USERNAME", (self.app / ".env").read_text(encoding="utf-8"))

    def test_unrelated_env_file_stops_the_update(self):
        self.write(self.app, "env", "contenuto qualunque")

        with self.assertRaises(updater.UpdateError):
            updater.resolve_env_name_conflict(self.app, lambda message: None)

        self.assertTrue((self.app / "env").is_file())

    def test_env_file_is_kept_when_credentials_already_exist(self):
        self.write(self.app, "env", "GENBA_USERNAME=tizio")
        self.write(self.app, ".env", "GENBA_USERNAME=caio")

        with self.assertRaises(updater.UpdateError):
            updater.resolve_env_name_conflict(self.app, lambda message: None)

        self.assertEqual((self.app / ".env").read_text(encoding="utf-8"), "GENBA_USERNAME=caio")

    def test_existing_env_directory_is_left_alone(self):
        (self.app / "env").mkdir()

        updater.resolve_env_name_conflict(self.app, lambda message: None)

        self.assertTrue((self.app / "env").is_dir())

    def test_state_round_trip(self):
        updater.save_state(self.app, "abcdef123", ["module.py", "app.py"])
        self.assertEqual(
            updater.load_state(self.app),
            {"sha": "abcdef123", "managed_files": ["app.py", "module.py"]},
        )


if __name__ == "__main__":
    unittest.main()
