"""Test configuration importer."""

import glob
import json
import os
import unittest
from jsonschema.exceptions import ValidationError

from sysbuilder.config import Config


class CfgTest(unittest.TestCase):
    """Test importing a good configuration."""

    def setUp(self):
        """Helper."""

        with open(
            "tests/data/sample_config_correct.json", encoding="utf-8", mode="r"
        ) as f:  # pylint: disable=C0103
            self.cfg = json.load(f)

    def test_cfg_good(self):
        """Test validation."""

        cfg = Config("tests/data/sample_config_good.json")

        self.assertEqual(cfg._cfg, self.cfg)  # pylint: disable=W0212

    def test_cfg_bad(self):
        """Test all bad configs."""

        bad_examples = glob.glob(
            os.path.join("tests", "data", "sample_config_bad_*.json")
        )

        for example in bad_examples:
            with self.subTest(example=example):
                with self.assertRaises((ValidationError, KeyError)):
                    Config(example)
