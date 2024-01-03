"""
This module concerns the VDIs that will be created by sysbuilder. 
"""

import logging
from typing import Any, Dict
from sysbuilder.config import Config
from sysbuilder.shell import Pacstrap
from sysbuilder.storage import Storage

log = logging.getLogger(__name__)


class VDI:
    """Virtual Disk Image class."""

    def __init__(
        self, cfg: Dict[Any, Any] | None = None, cfg_path: str | None = None
    ):
        """
        Init.

        # Params

          - cfg (dict): The configuration for storage and what should go on
            it.
          - cfg_path (str): A path to the JSON file containing configuration data.
        """

        if cfg is not None:
            self._cfg = Config(cfg)
        elif cfg_path is not None:
            self._cfg = Config.from_file(cfg_path)
        else:
            raise ValueError("Configs or a config file must be provided.")

        self._storage = Storage(self._cfg.get("storage"))

        self._storage.format()
        self._storage.mount()

        install_cfg = self._cfg.get("install")

        if install_cfg["base"] == "archlinux":
            self._archlinux_system()
        else:
            raise ValueError(
                "The base install system must be one of the following: ['archlinux']."
            )

    def _archlinux_system(self):
        """Install an arch based system."""

        packages = self._cfg.get("install").get("packages", [])

        # Archlinux install only supports Pacstrap
        Pacstrap.install(fs_root=self._storage.root, packages=packages)
