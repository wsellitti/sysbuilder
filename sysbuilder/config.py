"""Convert the configuration file into an object."""

import json
import logging
import os
from typing import Any, Dict
from sysbuilder.shell import Lsblk
from sysbuilder._validation import config

log = logging.getLogger(__name__)


class Config:
    """
    The configuration object contains all the data needed to create a
    functional system build.
    """

    def __init__(self, cfg: dict, check: bool = True):
        """
        Load configuration and validate.

        # Params

          - cfg (dict): See class docstring.
          - check (bool): If true run validation. Only useful in testing.
        """

        self._cfg = cfg

        if check:
            self._validate()

    @classmethod
    def from_file(cls, cfg: str):
        """Load configuration from a file."""

        with open(
            cfg, mode="r", encoding="utf-8"
        ) as f:  # pylint: disable=C0103
            return cls(cfg=json.load(f), check=True)

    def _validate(self) -> None:
        """
        Does JSON object validation then runs validation specific to certain
        values in the dictionary.
        """

        config.check(self._cfg)

        for function in dir(self):
            if function.startswith("_validate_"):
                self.__getattribute__(function)()  # pylint: disable=C2801

    def _validate_storage(self) -> None:
        """
        The JSON itself has been validated.

        Validates conditional values such as ['disk']['size'] being provided
        when ['disk']['type'] is "sparse".
        """

        disk = self._cfg["storage"]["disk"]

        disk["path"] = os.path.abspath(disk["path"])

        if disk["type"] in ["physical"]:
            Lsblk.list_one(disk["path"])  # Raises errors if not real.
        elif disk["type"] in ["sparse", "raw"]:
            if "size" not in disk.keys():
                raise KeyError("Missing size in disk description.")

    def get(self, key: Any, default: Any = None) -> Dict[Any, Any]:
        """Get's a configuration value."""

        if default is not None:
            self._cfg.get(key, default)

        return self._cfg[key]
