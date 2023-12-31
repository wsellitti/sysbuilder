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

    def tearDown(self):
        """Clean up."""

        loop = shell.Losetup.identify(self.img_path)
        shell.Losetup.detach(loop)

        os.remove(self.img_path)
        os.removedirs(os.path.dirname(self.img_path))

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

        my_device = storage.BlockDevice()
        my_device.update(lsblk["blockdevices"][0])

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

    def test_partitioning_image_file(self):
        """Test creating multiple partitions on an image file."""

        my_device = storage.BlockDevice.as_image_file(self.img_path)
        self.assertEqual(len(my_device._children), 0)

        my_device.add_part(
            start="",
            end="+4G",
            typecode="ef00",
            fs_type="vfat",
            fs_args=["-F", "32"],
        )
        self.assertEqual(len(my_device._children), 1)

        my_device.add_part(
            start="",
            end="+4G",
            typecode="8200",
            fs_type="swap",
        )
        self.assertEqual(len(my_device._children), 2)

        my_device.add_part(
            start="",
            end="",
            typecode="8300",
            fs_type="ext4",
        )
        self.assertEqual(len(my_device._children), 3)

        for child in my_device._children:
            self.assertIsInstance(child, storage.BlockDevice)

        self.assertEqual(
            [x.get("fstype") for x in my_device._children],
            ["vfat", "swap", "ext4"],
        )


class SparseStorageTesting(unittest.TestCase):
    """Test manipulating sparse disk images."""

    def setUp(self):
        """Set up."""
        tmpd = tempfile.mkdtemp()
        self.img_path = f"{tmpd}/disk.img"
        self.cfg = Config(
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

    def tearDown(self):
        """
        Clean up.

        All functions must implement the self.vdi object to test storage. The
        self.vdi object should be an object from the storage.Storage class.
        """

        self.vdi._device.unmount()
        shell.Losetup.detach(fp=self.vdi._device.path)

        os.remove(self.img_path)
        os.removedirs(os.path.dirname(self.img_path))

    def test_sparse_disk_creation(self):
        """Test creating a sparse loop file."""

        self.vdi = storage.Storage(storage=self.cfg.get("storage"))
        self.assertTrue(self.vdi._device.back_path == self.img_path)
        stats = os.stat(self.vdi._device.back_path)
        self.assertEqual(stats.st_size, 34359738368)

    def test_sparse_disk_partitioning(self):
        """Check partitioning a disk."""

        self.vdi = storage.Storage(storage=self.cfg.get("storage"))
        self.vdi.format()

        # There need to be as many partitions as were described in the configuration.
        self.assertEqual(
            len(self.vdi._device._children),
            len(self.cfg.get("storage")["layout"]),
        )

        fstypes = [c.get("fstype") for c in self.vdi._device._children]
        self.assertEqual(fstypes, ["vfat", "swap", "ext4"])

    def test_storage_mount(self):
        """Test Storage.mount()"""

        self.vdi = storage.Storage(storage=self.cfg.get("storage"))
        self.vdi.format()
        self.vdi.mount()

        for child in self.vdi._device.children:
            host_mountpoint = child.get("host_mountpoint")

            if host_mountpoint == "swap":
                continue

            self.assertTrue(os.path.exists(host_mountpoint))
            self.assertTrue(os.path.isdir(host_mountpoint))
            self.assertTrue(os.path.ismount(host_mountpoint))
