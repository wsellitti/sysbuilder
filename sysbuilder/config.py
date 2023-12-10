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

    # Configuration

    The configuration must contain at least the following top level keys:
      - storage (dict): Governs the storage type, partition scheme, and
        installed filesystems.
      - install (dict): Gooverns installed packages, enabled services,
        additional files, and the package manager.

    ## Storage

    The storage configuration must contain at least the following top level
    keys: ['disk', 'layout'].
      - disk (dict): Describes the storage "device". `disk` must contain at
        least the following keys: ['path', 'type', 'ptable'], but may also
        contain the keys ['size'].
          - path (str): This can be a path to either a device file (in /dev or
            /sys) or to a disk image file. `type` must be the appropriate
            corresponding value. If `type` is 'physical' the file provided in
            `path` must exist before this script is run.
          - type (str): This can be one of 3 values:
              - physical: The value in `path` must point to a physical block
                device.
              - sparse: The value in `path` will be assumed to be a virtual
                device. 'sparse' virtual devices will be created as a sparse
                files and will only allocate data as they're used.
              - raw: Similar to sparse, but raw devices will allocate all
                their intended storage at one time.
          - ptable (str): The partition table type, only supports 'gpt' at this
            time. A `ptable` value of 'gpt' will case sysbuilder to use `sgdisk`
            to partition the disk.
          - size (str): This should be a string shortened according to standard
            notation: '32G', '234M', '1T'. These values are in powers of 1024 not
            1000.
      - layout (list): Describes the partition layout on the storage device, as
        well as filesystems on those partitions. Each item in `layout` must
        contain at least the following keys: ['start', 'end', 'typecode',
        'filesystem'].
          - start (str): Sector where the partition should start. Values can be
            absolute or positions measured in standard notation: "K", "M", "G",
            "T". Providing and empty string "" will use the next available
            starting sector. Values beginning with a "+" will start the
            parittion that distance past the next available starting sector (ie,
            "+2G" will cause the next partition to start 2 gibibytes after the
            last partition ended). Values beginning with a "-"  will start the
            partition that distance from the next available ending sector with
            enough space (ie, "-2G" will create a partition that starts 2
            gibibytes before the ending most available sector).
          - end (str): Sector where the partition should end. Values can be
            absolute or positions measured in standard notation: "K", "M", "G",
            "T". Providing and empty string "" will use the next available
            ending sector from the starting sector. Values beginning with a "+"
            will end the partition that distance past the starting sector (ie,
            "+2G" will create a 2 gibibyte partition). Values beginning with a
            "-" will end the partition that distance from the next available
            ending sector (ie, "-2G" will create a partition that 2 gibibytes
            short of the maximum space available for that partiton).
          - typecode (str): A 4-digit hexadecimal value representing partition
            type codes, as returned from `sgdisk -L`.
          - filesystem (dict): Describes the filesystem that will be installed
            to the associated partition. `filesystem` must contain at least the
            following keys ['type', 'mountpoint'], but may also contain the keys
            ['label', 'args', 'label_flag', 'reformat'].
              - type (str): The filesystem type, as per `mkfs`. If the `type` is
                "swap" the command `mkswap` will be used instead of `mkfs -t`.
              - mountpoint (str): Where the filesystem will be mounted relative
                to the installed system (ie, the `mountpoint` for a filesystem
                that will be mounted on "/home" should be "/home"). If the
                `mountpoint` is "swap" the filesystem will be treated as swap space.
              - label (str): The filesystem label. No default.
              - label_flag (str): Some filesystems use nonstandard flags to
                create a filesystem, this is required if a label is provided for
                such an atypical filesystem partition. Defaults to "-L".
              - args (list): Additional arguments to be during the creation of
                the filesystem.

    ## Install

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
