"""Installation must preserve existing user definitions and be repeatable."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "install", Path(__file__).resolve().parents[1] / "scripts" / "install.py"
)
INSTALL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALL)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "agents"
        self.target.mkdir()

    def test_installs_all_and_repeat_is_noop(self):
        self.assertEqual(INSTALL.install(self.target), 10)
        for source in INSTALL.SOURCE.glob("*.md"):
            self.assertEqual(source.read_bytes(), (self.target / source.name).read_bytes())
        self.assertEqual(INSTALL.install(self.target), 0)

    def test_conflict_preflight_does_not_partially_install(self):
        existing = self.target / "devteam-security-reviewer.md"
        existing.write_text("User definition")
        with self.assertRaises(ValueError):
            INSTALL.install(self.target)
        self.assertEqual(list(self.target.iterdir()), [existing])
        self.assertEqual(existing.read_text(), "User definition")

    def test_explicit_replace_preserves_unrelated_agents(self):
        (self.target / "DevTeam.md").write_text("Old version")
        other = self.target / "custom.md"
        other.write_text("Unrelated agent")
        self.assertEqual(INSTALL.install(self.target, replace=True), 10)
        self.assertEqual(other.read_text(), "Unrelated agent")

    def test_replace_refuses_symlink(self):
        original = self.root / "original.md"
        original.write_text("User content")
        (self.target / "DevTeam.md").symlink_to(original)
        with self.assertRaises(ValueError):
            INSTALL.install(self.target, replace=True)
        self.assertEqual(original.read_text(), "User content")
        self.assertEqual(len(list(self.target.iterdir())), 1)


if __name__ == "__main__":
    unittest.main()
