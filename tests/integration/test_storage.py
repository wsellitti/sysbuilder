"""Test storage."""

# pylint: disable=W0212,W0201

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
        storage._LoopDevice.detach(self.vdi._device.path)

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
                    },
                    "layout": [
                        {
                            "start": "",
                            "end": "+100M",
                            "typecode": "ef00",
                            "filesystem": {
                                "type": "vfat",
                                "label": "EFI",
                                "args": ["-F", "32"],
                                "label_flag": "-n",
                                "mountpoint": "/efi",
                            },
                        },
                        {
                            "start": "",
                            "end": "+4G",
                            "typecode": "8200",
                            "filesystem": {
                                "type": "swap",
                                "label": "swap",
                                "mountpoint": "swap",
                            },
                        },
                        {
                            "start": "",
                            "end": "",
                            "typecode": "8300",
                            "filesystem": {
                                "type": "ext4",
                                "label": "root",
                                "mountpoint": "/",
                            },
                        },
                    ],
                }
            },
        )

        self.vdi = storage.Storage(storage=cfg.get("storage"))
        self.vdi.format()

        print(self.vdi._device._data)

        # There need to be as many partitions as were described in the configuration.
        self.assertEqual(
            len(self.vdi._device._children), len(cfg.get("storage")["layout"])
        )
