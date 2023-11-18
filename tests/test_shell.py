"""Test shell module."""

# pylint: disable=C0103

import os
from subprocess import CalledProcessError
import tempfile
import unittest
from jsonschema import validate
from sysbuilder.shell import DD, Losetup, Lsblk, Mkfs, PartProbe, SGDisk
from tests.data.lsblk_validate import validate_json


class DdTest(unittest.TestCase):
    """Test instances of dd command."""

    def setUp(self):
        """Test path."""
        self.file = os.path.join(tempfile.mkdtemp(), "disk.img")

    def tearDown(self):
        """Clean up"""

        os.remove(self.file)
        os.removedirs(os.path.dirname(self.file))

    def test_dd_sparse(self):
        """Test sparse file creation."""

        DD.write_file(
            input_file="/dev/zero",
            output_file=self.file,
            count="2048",
            convs=["sparse"],
        )

        blocks_utilized = os.stat(self.file).st_blocks

        self.assertEqual(blocks_utilized * 512, 0)

    def test_dd(self):
        """Test file creation."""

        DD.write_file(
            input_file="/dev/zero", output_file=self.file, count="2048"
        )

        blocks_utilized = os.stat(self.file).st_blocks

        self.assertEqual(blocks_utilized * 512, 2147483648)


class FormatDiskTest(unittest.TestCase):
    """Test runs of partprobe."""

    def setUp(self):
        """Test file."""

        self.file = os.path.join(tempfile.mkdtemp(), "disk.img")
        DD.write_file(
            input_file="/dev/zero",
            output_file=self.file,
            count="2048",
            convs=["sparse"],
        )
        Losetup.attach(self.file)
        self.dev = Losetup.identify(self.file)

    def tearDown(self):
        """Clean up"""

        Losetup.detach(self.dev)
        os.remove(self.file)
        os.removedirs(os.path.dirname(self.file))

    def test_sgdisk(self):
        """Test sgdisk"""

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]
        self.assertIsNone(loop.get("children"))

        SGDisk.create_partition(
            devpath=self.dev,
            part_number="1",
            start_sector="",
            end_sector="+512M",
        )
        SGDisk.create_partition(
            devpath=self.dev,
            part_number="2",
            start_sector="",
            end_sector="+512M",
        )
        SGDisk.create_partition(
            devpath=self.dev,
            part_number="3",
            start_sector="",
            end_sector="",
        )

        SGDisk.set_partition_type(
            devpath=self.dev, part_number="1", typecode="ef00"
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="2", typecode="8200"
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="3", typecode="8300"
        )

        PartProbe.probe_device(self.dev)

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]
        self.assertEqual(len(loop.get("children", [])), 3)

    def test_fs_creation(self):
        """Test mkfs"""

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]
        self.assertIsNone(loop.get("children"))

        SGDisk.create_partition(
            devpath=self.dev,
            part_number="1",
            start_sector="",
            end_sector="+512M",
        )
        SGDisk.create_partition(
            devpath=self.dev,
            part_number="2",
            start_sector="",
            end_sector="+512M",
        )
        SGDisk.create_partition(
            devpath=self.dev,
            part_number="3",
            start_sector="",
            end_sector="",
        )

        SGDisk.set_partition_type(
            devpath=self.dev, part_number="1", typecode="ef00"
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="2", typecode="8200"
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="3", typecode="8300"
        )

        PartProbe.probe_device(self.dev)

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]

        loopc1 = loop["children"][0]
        loopc2 = loop["children"][1]
        loopc3 = loop["children"][2]

        self.assertIsNone(loopc1["fstype"])
        self.assertIsNone(loopc2["fstype"])
        self.assertIsNone(loopc3["fstype"])

        Mkfs.create(devpath=loopc1["path"], fstype="vfat", fs_args=["-F", "32"])
        Mkfs.create(devpath=loopc3["path"], fstype="ext4")

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]

        loopc1 = loop["children"][0]
        loopc2 = loop["children"][1]
        loopc3 = loop["children"][2]

        self.assertEqual(loopc1["fstype"], "vfat")
        self.assertEqual(loopc3["fstype"], "ext4")
