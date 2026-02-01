from src.detection.flagged_evidence_saver import FlaggedEvidenceSaver
import os
import sys
import shutil
import unittest
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestSecureDelete(unittest.TestCase):
    def setUp(self):
        self.test_dir = PROJECT_ROOT / "tests" / "temp_evidence"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.saver = FlaggedEvidenceSaver(output_dir=str(self.test_dir))

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_secure_delete_file(self):
        # Create a dummy file
        test_file = self.test_dir / "secret.txt"
        content = b"Super secret content"
        with open(test_file, "wb") as f:
            f.write(content)

        self.assertTrue(test_file.exists())

        # Determine file size
        size = test_file.stat().st_size

        # Test secure delete
        self.saver._secure_delete_file(str(test_file))

        self.assertFalse(test_file.exists())

    def test_secure_delete_recursive(self):
        # Create nested directory structure
        subdir = self.test_dir / "event_1"
        subdir.mkdir()

        file1 = subdir / "frame.jpg"
        file2 = subdir / "metadata.json"

        with open(file1, "w") as f:
            f.write("image data")
        with open(file2, "w") as f:
            f.write("{}")

        self.assertTrue(file1.exists())

        # Test recursive delete
        self.saver._secure_delete_recursive(str(subdir))

        self.assertFalse(subdir.exists())
        self.assertFalse(file1.exists())


if __name__ == '__main__':
    unittest.main()
