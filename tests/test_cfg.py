"""Test configuration importer."""

import json
import unittest
from jsonschema.exceptions import ValidationError

from sysbuilder.config import Config


class GoodCfgTest(unittest.TestCase):
    """Test importing a good configuration."""

    def setUp(self):
        """Helper."""

        with open(
            "tests/data/sample_config_correct.json", encoding="utf-8", mode="r"
        ) as f:  # pylint: disable=C0103
            self.cfg = json.load(f)

    def test_cfg_good(self):
        """Test validation."""

        cfg = Config.from_file("tests/data/sample_config_good.json")

        self.assertEqual(cfg._cfg, self.cfg)  # pylint: disable=W0212


class BadCfgTest(unittest.TestCase):
    """Test importing a good configuration."""

    def _template(self, test_name):
        """Template function."""

        json_path = f"tests/data/sample_config_bad_{test_name}.json"
        with self.assertRaises((ValidationError, KeyError)):
            Config(json_path)

    # pylint: disable=C0116
    def test_cfg_bad_layout_items(self):
        self._template("layout_items")

    def test_cfg_bad_missing_disk(self):
        self._template("missing_disk")

    def test_cfg_bad_missing_layout(self):
        self._template("missing_layout")

    def test_cfg_bad_vdisk_without_size(self):
        self._template("vdisk_without_size")

    def test_cfg_bad_layout_incorrect_mountpoint(self):
        self._template("layout_incorrect_mountpoint")
