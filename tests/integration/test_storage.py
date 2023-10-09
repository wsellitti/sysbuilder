"""Test storage."""

import tempfile
import unittest
from sysbuilder.config import Config
from sysbuilder import storage


class SparseStorageTesting(unittest.TestCase):
    """Test manipulating sparse disk images."""

    def setUp(self):
        """Set up."""
        tmpd = tempfile.mkdtemp()
        self.img_path = f"{tmpd}/disk.img"

    def tearDown(self):
        """
        Clean up.

        All functions must implement the self.vdi object to test storage. The
        self.vdi object should be an object from the storage.Storage class.
        """

        self.vdi._device.unmount()

    def test_sparse_disk_creation(self):
        """Test creating a sparse loop file."""

        cfg = Config(
            check=False,
            cfg={
                "storage": {
                    "disk": {
                        "path": self.img_path,
                        "type": "sparse",
                        "ptable": "gpt",
                        "size": "32G",
                    }
                }
            },
        )

        self.vdi = storage.Storage(storage=cfg.get("storage"))
        self.assertTrue(self.vdi._device.back_path == self.img_path)

    def test_sparse_disk_partitioning(self):
        """Check partitioning a disk."""

        cfg = Config(
            check=False,
            cfg={
                "storage": {
                    "disk": {
                        "path": self.img_path,
                        "type": "sparse",
                        "ptable": "gpt",
                        "size": "32G",
                    }
                }
            },
        )

        self.vdi = storage.Storage(storage=cfg.get("storage"))
        self.vdi.format()
        self.assertTrue(self.vdi._device.back_path == self.img_path)
