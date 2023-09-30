"""Convert the configuration file into an object."""

import json
import logging

log = logging.getLogger(__name__)


class Config:
    def __init__(self, cfg):
        with open(cfg_path, mode="r", encoding="utf-8") as cfg_file:
            self._cfg = json.load(cfg_file)
