# pylint: disable=W0212

"""Test configuration importer."""

import json
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


class GoodCfgTest(unittest.TestCase):
    """Test importing a good configuration."""

    def test_init(self):
        """Test validation."""

        _cfg = get_cfg()

        cfg_path = "tests/data/sample_config_good.json"
        cfg = Config(cfg_path)

        self.assertEqual(cfg._cfg, _cfg)


class BadCfgTest(unittest.TestCase):
    """Test importing bad configurations."""

    def _test_bad(self, sub: str):
        """Bad tests are all the same structure."""

        _cfg = get_cfg()

        cfg_path = f"tests/data/sample_config_{sub}.json"
        with self.assertRaises(ValidationError):
            Config(cfg_path)

    def test_init_missing_disk(self):
        """Test validation when ['storage']['disk'] is missing."""

        self._test_bad("missing_disk")
