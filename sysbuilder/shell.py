"""Shell commands."""

import json
import logging
import os
import stat
import subprocess
import time
from typing import Any, Dict, List, Literal

log = logging.getLogger(__name__)


class _Shell:
    """Generic _Shell class."""

    @staticmethod
    def command(func) -> Any:
        """
        Run test

        # Params
          - args (list): Arguments for the provided function.
          - kwargs (dict): Keyword arguments for the provided function.

        """

        def inner(*args, **kwargs):
            log.debug(func.__name__)
            return func(*args, **kwargs)

        return inner


class DD(_Shell):
    """Wraps `dd` shell command."""

    @_Shell.command
    def run(
        self,
        output_file: str,
        count: int,
        bs: str = "1M",
        convs: List[str] | None = None,
        input_file: str = "/dev/zero",
    ) -> None:
        """
        dd wrapper

        Parameters are mostly based off of defined dd parameters.
        """

        output_file = os.path.abspath(output_file)

        if os.path.exists(output_file):
            raise FileExistsError(output_file)

        command = [
            "dd",
            f"if={input_file}",
            f"of={output_file}",
            f"bs={bs}",
            f"count={count}",
        ]

        if convs is not None:
            conversions = ",".join(convs)
            command.append(f"conv={conversions}")

        log.debug(command)

        subprocess.run(
            command, capture_output=True, check=True, encoding="utf-8"
        )


class Losetup(_Shell):
    """Wraps `losetup` shell command."""

    @_Shell.command
    def run(self, fp: str, test: Literal["attach", "detach"]) -> None:
        """
        Wraps losetup.

        # Params

          - fp (str): The filepath to the blockdevice or backing file. If fp
            is a loop block device the losetup function will attempt to
            deactivate, otherwise the losetup function will attempt to
            activate as a loop device.
          - test (str): Must be one of:
              - attach: Adds a file as a loop device if it's not one already.
                Does nothing otherwise.
              - detach: Removes the file from being a loop device if it is
                one. Does nothing otherwise.

        **THERE IS NO WAY FOR LOSETUP TO DISTINGUISH A FILE THAT SHOULD NOT BE A
        LOOPDEVICE FROM ONE THAT SHOULD. THIS ACTION IS POTENTIALLY DESTRUCTIVE.**
        """

        fp = os.path.abspath(fp)

        if test == "attach":
            if stat.S_ISBLK(os.stat(fp).st_mode) > 0:
                raise ValueError(f"{fp} is a device file already.")

        if test == "detach":
            if stat.S_ISBLK(os.stat(fp).st_mode) == 0:
                raise ValueError(f"{fp} is not a device file.")

        args = {
            "attach": [
                "--show",
                "--find",
                "--nooverlap",
                "--partscan",
            ],
            "detach": ["--detach"],
        }

        command = ["sudo", "losetup"]
        command.extend(args[test])
        command.append(fp)

        subprocess.run(
            command, check=True, capture_output=True, encoding="utf-8"
        )


class Lsblk(_Shell):
    """Wrapps `lsblk` shell command."""

    @_Shell.command
    def run(self, *args) -> List[Dict[Any, Any]]:
        """
        lsblk wrapper

        args: Active block device files.
        """

        for dev in args:
            if stat.S_ISBLK(os.stat(dev).st_mode) == 0:
                raise ValueError(f"{dev} is not a device file.")

        command = ["lsblk", "--output-all", "--json"]
        command.extend(args)

        result = subprocess.run(
            command,
            capture_output=True,
            check=True,
            encoding="utf-8",
        )

        return json.loads(result.stdout)["blockdevices"]


def partprobe(*args):
    """partprobe wrapper"""

    for dev in args:
        if stat.S_ISBLK(os.stat(dev).st_mode) == 0:
            raise ValueError(f"{dev} is not a device file.")

    command = ["sudo", "partprobe"]
    command.extend(args)

    subprocess.run(command, check=True, capture_output=True)


class SGDisk(_Shell):
    """Wraps `sgdisk` shell command."""

    @_Shell.command
    def run(self, devpath: str, layout: Dict[str, Any]) -> None:
        """
        sgdisk wrapper

        # Params

          - devpath (str): Path to the device.
          - layout (list): How the partitions should be laid out on the disk
            provided by `devpath`. Each item represents a different partition.

        ## Layout

        Each object provided by `layout` must contain at least one of the
        following sets of keys (the name of the set is not a value that needs to
        be provided, the type will be determined based on the keys in the
        dictionary).

        Partition:
          - part_number (str): The partition number.
          - start_sector (str): The on-disk sector a partition should start at.
            This can be an absolute sector number or a relative value measured in
            kibibytes, mebibytes, gibibytes, tebibytes, or prebibytes.
          - end_sector (str): The on-disk sector a partition should end at. This
            can be an absolute sector number or a relative value measured in
            kibibytes, mebibytes, gibibytes, tebibytes, or prebibytes.

        Typecode:
          - part_number (int): The partition number.
          - typecode (str): A 4-character hexadecimal value representing
            filesystem type codes.
        """

        if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
            raise ValueError(f"{devpath} is not a device file.")

        command = ["sgdisk"]

        for flag_dict in layout:
            part_num = flag_dict["part_num"]
            start_sector = flag_dict.get("start_sector")
            end_sector = flag_dict.get("end_sector")
            typecode = flag_dict.get("typecode")
            if start_sector is not None and end_sector is not None:
                addon = [
                    "--new",
                    ":".join([part_num, str(start_sector), str(end_sector)]),
                ]
            elif typecode is not None:
                addon = [
                    "--typecode",
                    ":".join([part_num, typecode]),
                ]
            else:
                raise KeyError(
                    "Either start_sector and end_sector or typecode must be provided!"
                )
            command.extend(addon)
            command.append(devpath)

        subprocess.run(
            command, check=True, capture_output=True, encoding="utf-8"
        )
