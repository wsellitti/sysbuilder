"""Test storage."""

# pylint: disable=W0212,W0201

import os
import tempfile
import unittest
from jsonschema import validate
from sysbuilder.config import Config
from sysbuilder import storage
from sysbuilder import shell
from tests.data.lsblk_validate import validate_json


class BlockDeviceTest(unittest.TestCase):
    """Test BlockDevice class."""

    def setUp(self):
        """Set up."""

        tmpd = tempfile.mkdtemp()
        self.img_path = os.path.join(tmpd, "disk.img")

    def test_init(self):
        """Test BlockDeviceInit"""

        shell.DD.write_file(
            input_file="/dev/zero",
            output_file=self.img_path,
            count="32768",
            convs=["sparse"],
        )

        shell.Losetup.attach(fp=self.img_path)
        dev = shell.Losetup.identify(fp=self.img_path)

        lsblk = shell.Lsblk.list_one(devpath=dev)

        my_device = storage.BlockDevice(**lsblk["blockdevices"][0])

        validate([my_device._data], validate_json)

    def test_from_device_path(self):
        """Test BlockDevice from_device_path"""

        shell.DD.write_file(
            input_file="/dev/zero",
            output_file=self.img_path,
            count="32768",
            convs=["sparse"],
        )

        shell.Losetup.attach(fp=self.img_path)
        dev = shell.Losetup.identify(fp=self.img_path)

        my_device = storage.BlockDevice.from_device_path(devpath=dev)
        validate([my_device._data], validate_json)

    def test_as_image_file(self):
        """Test BlockDevice as_image_file"""

        my_device = storage.BlockDevice.as_image_file(self.img_path)

        self.assertTrue(os.path.exists(self.img_path))
        validate([my_device._data], validate_json)


# class SparseStorageTesting(unittest.TestCase):
#     """Test manipulating sparse disk images."""

#     def setUp(self):
#         """Set up."""
#         tmpd = tempfile.mkdtemp()
#         self.img_path = f"{tmpd}/disk.img"

#     def tearDown(self):
#         """
#         Clean up.

#         All functions must implement the self.vdi object to test storage. The
#         self.vdi object should be an object from the storage.Storage class.
#         """

#         self.vdi._device.unmount()
#         shell.Losetup.detach(fp=self.vdi._device.path)

#     def test_sparse_disk_creation(self):
#         """Test creating a sparse loop file."""

#         cfg = Config(
#             check=False,
#             cfg={
#                 "storage": {
#                     "disk": {
#                         "path": self.img_path,
#                         "type": "sparse",
#                         "ptable": "gpt",
#                         "size": "32G",
#                     }
#                 }
#             },
#         )

#         self.vdi = storage.Storage(storage=cfg.get("storage"))
#         self.assertTrue(self.vdi._device.back_path == self.img_path)
#         stats = os.stat(self.vdi._device.back_path)
#         self.assertEqual(stats.st_size, 34359738368)

#     def test_sparse_disk_partitioning(self):
#         """Check partitioning a disk."""

#         cfg = Config(
#             check=False,
#             cfg={
#                 "storage": {
#                     "disk": {
#                         "path": self.img_path,
#                         "type": "sparse",
#                         "ptable": "gpt",
#                         "size": "32G",
#                     },
#                     "layout": [
#                         {
#                             "start": "",
#                             "end": "+100M",
#                             "typecode": "ef00",
#                             "filesystem": {
#                                 "type": "vfat",
#                                 "label": "EFI",
#                                 "args": ["-F", "32"],
#                                 "label_flag": "-n",
#                                 "mountpoint": "/efi",
#                             },
#                         },
#                         {
#                             "start": "",
#                             "end": "+4G",
#                             "typecode": "8200",
#                             "filesystem": {
#                                 "type": "swap",
#                                 "label": "swap",
#                                 "mountpoint": "swap",
#                             },
#                         },
#                         {
#                             "start": "",
#                             "end": "",
#                             "typecode": "8300",
#                             "filesystem": {
#                                 "type": "ext4",
#                                 "label": "root",
#                                 "mountpoint": "/",
#                             },
#                         },
#                     ],
#                 }
#             },
#         )

#         self.vdi = storage.Storage(storage=cfg.get("storage"))
#         self.vdi.format()

#         # There need to be as many partitions as were described in the configuration.
#         self.assertEqual(
#             len(self.vdi._device._children), len(cfg.get("storage")["layout"])
#         )

#         fstypes = [c.get("fstype") for c in self.vdi._device._children]
#         self.assertEqual(fstypes, ["vfat", "swap", "ext4"])
