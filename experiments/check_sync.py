"""File-preservation checks for the independent Ubuntu updater."""
import runpy
import tempfile
import unittest
from pathlib import Path


helpers = runpy.run_path(str(Path(__file__).resolve().parents[1] / "ubuntu/update_local.py"))


class SyncChecks(unittest.TestCase):
    def test_different_existing_result_is_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "incoming.json"
            project = root / "project"
            project.mkdir()
            target = project / "result.json"
            source.write_bytes(b"incoming")
            target.write_bytes(b"student result")
            self.assertEqual(helpers["copy_file"](source, target, project, preserve_existing=True), "preserved")
            self.assertEqual(target.read_bytes(), b"student result")

    def test_update_replaces_content_and_preserves_unchanged_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.py"
            project = root / "project"
            project.mkdir()
            target = project / "sub/code.py"
            source.write_bytes(b"print('new')\n")
            self.assertEqual(helpers["copy_file"](source, target, project), "updated")
            stamp = target.stat().st_mtime_ns
            self.assertEqual(helpers["copy_file"](source, target, project), "unchanged")
            self.assertEqual(target.stat().st_mtime_ns, stamp)
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_destination_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "incoming.py"
            project = root / "project"
            project.mkdir()
            source.write_bytes(b"new")
            target = project / "../outside.py"
            with self.assertRaisesRegex(ValueError, "leaves"):
                helpers["copy_file"](source, target, project)
            self.assertFalse(target.exists())

    def test_only_changed_controller_is_backed_up(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, current = root / "new.py", root / "active.py"
            source.write_bytes(b"new")
            current.write_bytes(b"working")
            backup = helpers["backup_controller"](source, current, root / "backups")
            self.assertEqual(backup.read_bytes(), b"working")
            current.write_bytes(b"new")
            self.assertIsNone(helpers["backup_controller"](source, current, root / "backups"))


if __name__ == "__main__":
    unittest.main()
