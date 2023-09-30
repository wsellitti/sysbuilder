"""Convert the configuration file into an object."""

import json
import logging
from typing import Any

log = logging.getLogger(__name__)


class Config:
    def __init__(self, cfg):
        with open(cfg, mode="r", encoding="utf-8") as f:
            self._cfg = json.load(f)

    def get(self, key: Any) -> dict:
        """Get's a configuration value."""
        return self._cfg.get(key)
