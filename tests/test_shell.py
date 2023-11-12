"""Test shell module."""

# pylint: disable=C0103

import os
import stat
import tempfile
import unittest
from jsonschema import validate
from sysbuilder.shell import DD, Losetup, Lsblk
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

        dd = DD()
        dd.run(self.file, count="2048", convs=["sparse"])

        blocks_utilized = os.stat(self.file).st_blocks

        self.assertEqual(blocks_utilized * 512, 0)

    def test_dd(self):
        """Test sparse file creation."""

        dd = DD()
        dd.run(self.file, count="2048")

        blocks_utilized = os.stat(self.file).st_blocks

        self.assertEqual(blocks_utilized * 512, 2147483648)


class losetupTest(unittest.TestCase):
    """Test instances of losetup command."""

    def setUp(self):
        """Test file."""

        self.file = os.path.join(tempfile.mkdtemp(), "disk.img")
        dd = DD()
        dd.run(self.file, count="2048", convs=["sparse"])

    def tearDown(self):
        """Clean up"""

        os.remove(self.file)
        os.removedirs(os.path.dirname(self.file))

    def test_losetup(self):
        """Test losetup attach and detach"""

        losetup = Losetup()
        losetup.run(self.file, test="attach")

        dev = "/dev/loop0"
        self.assertTrue(stat.S_ISBLK(os.stat(dev).st_mode))

        losetup.run(dev, test="detach")
        self.assertFalse(os.path.exists(dev))
        self.assertFalse(stat.S_ISBLK(os.stat(dev).st_mode))


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
        lsblk = Lsblk()
        results = lsblk.run()
        self._lsblk_recurse(results)

    def test_lsblk_sda(self):
        """lsblk with one device argument"""
        lsblk = Lsblk()
        results = lsblk.run("/dev/sda")
        self._lsblk_recurse(results)

    def test_lsblk_fail(self):
        """lsblk with one nondevice argument"""
        with self.assertRaises(ValueError):
            lsblk = Lsblk()
            lsblk.run("/bin/ls")


class partprobeTest(unittest.TestCase):
    """Test runs of partprobe."""

    def test_partprobe(self):
        """Test partprobe"""