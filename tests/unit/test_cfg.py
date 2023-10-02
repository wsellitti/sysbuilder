"""Test configuration importer."""

import glob
import json
import os
import re
import unittest
from jsonschema.exceptions import ValidationError

from sysbuilder.config import Config


class CfgTest(unittest.TestCase):
    """Test importing a good configuration."""

    def __init__(self, *args, **kwargs):
        """Wrap init to add a bunch of generated tests."""

        bad_examples = glob.glob(
            os.path.join("tests", "data", "sample_config_bad_*.json")
        )

        for bad_example in bad_examples:
            example_name = re.search(
                "sample_config_bad_(.+).json", bad_example
            ).group(1)
            test = self._template(bad_example)
            test.__name__ = f"test_cfg_bad_{example_name}"

            # Add tests to test somehow
            self.__setattr__(test.__name__, test)

        super().__init__(*args, **kwargs)

    def _template(self, json_path: str):
        """Return template test function."""

        def inner():
            with self.assertRaises((ValidationError, KeyError)):
                Config(json_path)

        return inner

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

    def test_cfg_bad_layout_items(self):
        """Test bad layout."""

        with open(
            "tests/data/sample_config_bad_layout_items.json",
            encoding="utf-8",
            mode="r",
        ) as f:  # pylint: disable=C0103
            cfg = json.load(f)

            Config("tests/data/sample_config_bad_layout_items.json")
