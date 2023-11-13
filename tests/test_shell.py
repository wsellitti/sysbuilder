"""Test shell module."""

# pylint: disable=C0103

import os
from subprocess import CalledProcessError
import tempfile
import unittest
from jsonschema import validate
from sysbuilder.shell import DD, Losetup, Lsblk, PartProbe, SGDisk
from tests.data.lsblk_validate import validate_json


class ddTest(unittest.TestCase):
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

        DD.run(self.file, count="2048", convs=["sparse"])

        blocks_utilized = os.stat(self.file).st_blocks

        self.assertEqual(blocks_utilized * 512, 0)

    def test_dd(self):
        """Test file creation."""

        DD.run(self.file, count="2048")

        blocks_utilized = os.stat(self.file).st_blocks

        self.assertEqual(blocks_utilized * 512, 2147483648)


class losetupTest(unittest.TestCase):
    """Test instances of losetup command."""

    def setUp(self):
        """Test file."""

        self.file = os.path.join(tempfile.mkdtemp(), "disk.img")
        DD.run(output_file=self.file, count="2048", convs=["sparse"])
        if not os.path.exists(self.file):
            raise FileNotFoundError(self.file)

    def tearDown(self):
        """Clean up"""

        os.remove(self.file)
        os.removedirs(os.path.dirname(self.file))

    def test_losetup(self):
        """Test losetup attach and detach"""

        Losetup.attach(self.file)

        dev = Losetup.identify(self.file)
        Lsblk.lookup(dev)

        Losetup.detach(dev)
        with self.assertRaises(CalledProcessError):
            Lsblk.lookup(dev)  # The files still exist but lsblk fails.


class lsblkTest(unittest.TestCase):
    """Test instances of lsblk command."""

    @staticmethod
    def _lsblk_recurse(testlist: list):
        validate(testlist, validate_json)
        for result in testlist:
            children = result.get("children")
            if children is not None:
                lsblkTest._lsblk_recurse(children)

    def test_lsblk_all(self):
        """lsblk with no arguments"""

        results = Lsblk.lookup()["blockdevices"]
        self._lsblk_recurse(results)

    def test_lsblk_sda(self):
        """lsblk with one device argument"""

        # Generally people have sata or nvme, sometimes even both
        for disk_name in ["/dev/sda", "/dev/nvme0n1", "/dev/vda"]:
            try:
                results = Lsblk.lookup(disk_name)["blockdevices"]
                self._lsblk_recurse(results)
            except FileNotFoundError:
                results = None
                continue

    def test_lsblk_fail(self):
        """lsblk with one nondevice argument"""

        with self.assertRaises(ValueError):
            Lsblk.lookup("/bin/ls")


class partprobeTest(unittest.TestCase):
    """Test runs of partprobe."""

    def test_partprobe(self):
        """Test partprobe"""
