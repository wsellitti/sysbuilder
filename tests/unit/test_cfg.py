# pylint: disable=W0212

"""Test configuration importer."""

import glob
import json
import os
from jsonschema.exceptions import ValidationError
import unittest

from sysbuilder.config import Config


def get_cfg():
    """Helper."""

    _cfg_path = "tests/data/sample_config_correct.json"
    with open(
        _cfg_path, encoding="utf-8", mode="r"
    ) as f:  # pylint: disable=C0103
        return json.load(f)


class CfgTest(unittest.TestCase):
    """Test importing a good configuration."""

    def test_cfg_good(self):
        """Test validation."""

        _cfg = get_cfg()

        cfg_path = "tests/data/sample_config_good.json"
        cfg = Config(cfg_path)

        self.assertEqual(cfg._cfg, _cfg)

    def test_cfg_bad(self):
        """Test all bad configs."""

        bad_examples = glob.glob(
            os.path.join("tests", "data", "sample_config_bad_*.json")
        )

        for example in bad_examples:
            with self.subTest(_cfg=get_cfg(), example=example):
                with self.assertRaises(ValidationError):
                    Config(example)
