"""
Test sysbuilder.image classes
"""

import logging
import unittest
from sysbuilder.image import VDI

log = logging.getLogger(__name__)


class VDITest(unittest.TestCase):
    """Test VDI class."""

    def tearDown(self):
        """Cleanup"""

        self.vdi._storage._device.unmount()

    def test_init(self):
        """Test VDI.__init__"""

        self.vdi = VDI(cfg_path="tests/data/test_vdi.json")
