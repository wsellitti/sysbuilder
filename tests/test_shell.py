"""Test shell module."""

# pylint: disable=C0103

from jsonschema import validate
import os
import tempfile
import unittest
from sysbuilder.shell import dd, lsblk
from tests.data.lsblk_validate import validate_json


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
        results = lsblk()
        self._lsblk_recurse(results)

    def test_lsblk_sda(self):
        """lsblk with one device argument"""
        results = lsblk("/dev/sda")
        self._lsblk_recurse(results)

    def test_lsblk_fail(self):
        """lsblk with one nondevice argument"""
        with self.assertRaises(ValueError):
            lsblk("/bin/ls")


class partprobeTest(unittest.TestCase):
    """Test runs of partprobe."""

    def test_partprobe(self):
        """Test partprobe"""
