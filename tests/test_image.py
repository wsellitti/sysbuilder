"""
Test sysbuilder.image classes
"""

# pylint: disable=W0212,W0201


import logging
import os
import unittest
from sysbuilder.image import VDI

log = logging.getLogger(__name__)


class VDITest(unittest.TestCase):
    """Test VDI class."""

    def tearDown(self):
        """Cleanup"""

        if getattr(self, "vdi", None) is not None:
            self.vdi._storage._device.unmount()
            self.vdi._storage._device.close()

            os.remove(self.vdi._storage._device.back_path)

    def test_init(self):
        """Test VDI.__init__"""

        self.vdi = VDI(cfg_path="tests/data/test_vdi.json")
