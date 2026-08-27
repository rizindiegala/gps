import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import commons
except ImportError:  # le dipendenze dell'app non sono installate, ad esempio in CI
    commons = None


@unittest.skipIf(commons is None, "le dipendenze dell'app non sono installate")
class CredentialsFileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, name: str) -> Path:
        path = self.root / name
        path.write_text("GENBA_USERNAME=tizio\n", encoding="utf-8")
        return path

    def test_standard_name_is_found(self):
        expected = self.write(".env")

        self.assertEqual(commons.get_credentials_file(self.root), expected)

    def test_dotless_name_is_accepted(self):
        expected = self.write("env.txt")

        self.assertEqual(commons.get_credentials_file(self.root), expected)

    def test_italian_name_is_accepted(self):
        expected = self.write("credenziali.txt")

        self.assertEqual(commons.get_credentials_file(self.root), expected)

    def test_name_with_appended_extension_is_accepted(self):
        expected = self.write(".env.txt")

        self.assertEqual(commons.get_credentials_file(self.root), expected)

    def test_standard_name_wins_over_the_alternatives(self):
        expected = self.write(".env")
        self.write("env.txt")
        self.write("credenziali.txt")

        self.assertEqual(commons.get_credentials_file(self.root), expected)

    def test_missing_file_returns_nothing(self):
        self.assertIsNone(commons.get_credentials_file(self.root))

    def test_directory_is_not_mistaken_for_the_file(self):
        (self.root / "env.txt").mkdir()

        self.assertIsNone(commons.get_credentials_file(self.root))


if __name__ == "__main__":
    unittest.main()
