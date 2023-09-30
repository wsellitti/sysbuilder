"""Helper functions."""

import json
import logging

log = logging.getLogger(__name__)


def read_config(cfg_path: str) -> dict:
    """Return the json data of the file at fp."""

    with open(cfg_path, mode="r", encoding="utf-8") as cfg_file:
        return json.load(cfg_file)
