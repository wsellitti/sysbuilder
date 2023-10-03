"""Storage module testing."""

import unittest
from sysbuilder.storage import _BlockDevice as BlockDevice


class BlockDevTest(unittest.TestCase):
    def test_get_child_devices(self):
        """Test _BlockDevice.get_child_devices()"""
