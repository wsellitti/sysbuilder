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
    @staticmethod
    def run(
        output_file: str,
        count: str,
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
    """
    Wraps `losetup` shell command.

    **THERE IS NO WAY FOR LOSETUP TO DISTINGUISH A FILE THAT SHOULD NOT BE A
    LOOPDEVICE FROM ONE THAT SHOULD. THIS ACTION IS POTENTIALLY DESTRUCTIVE.**
    """

    @_Shell.command
    @staticmethod
    def attach(fp: str) -> None:
        """
        Wraps losetup.

        For activating files as loop devices only.

        # Params

          - fp (str): Path to target file.
        """

        fp = os.path.abspath(fp)

        if stat.S_ISBLK(os.stat(fp).st_mode) > 0:
            raise ValueError(f"{fp} is not a device file.")

        args = [
            "--show",
            "--find",
            "--nooverlap",
            "--partscan",
        ]

        command = ["sudo", "losetup"]
        command.extend(args)
        command.append(fp)

        subprocess.run(
            command, check=True, capture_output=True, encoding="utf-8"
        )

    @_Shell.command
    @staticmethod
    def detach(fp: str) -> None:
        """
        Wraps losetup.

        For deactivating loop devices.

        # Params

          - fp (str): Path to target file.
        """

        fp = os.path.abspath(fp)

        if stat.S_ISBLK(os.stat(fp).st_mode) == 0:
            raise ValueError(f"{fp} is a device file already.")

        args = ["--detach"]

        command = ["sudo", "losetup"]
        command.extend(args)
        command.append(fp)

        subprocess.run(
            command, check=True, capture_output=True, encoding="utf-8"
        )

    @_Shell.command
    @staticmethod
    def detach_all() -> None:
        """
        Wraps losetup.

        For deactivating all loop devices.
        """

        args = ["--detach-all"]

        command = ["sudo", "losetup"]
        command.extend(args)

        subprocess.run(
            command, check=True, capture_output=True, encoding="utf-8"
        )

    @_Shell.command
    @staticmethod
    def identify(fp: str) -> str:
        """
        Wraps losetup.

        Finds which loop device is backed by the file `fp`.
        """

        fp = os.path.abspath(fp)

        if not os.path.exists(fp):
            raise ValueError(f"{fp} does not exist!")

        args = ["--find", "--show"]

        command = ["sudo", "losetup"]
        command.extend(args)
        command.append(fp)

        result = subprocess.run(
            command, check=True, capture_output=True, encoding="utf-8"
        )

        return result.stdout.strip()

    @_Shell.command
    @staticmethod
    def lookup(fps: List[str] | None = None) -> Dict[Any, Any]:
        """
        Wraps losetup.

        Gets details for a loop device.

        # Params

          - fps (list): One or more block device file paths.

        # Returns

        (dict) An object describing loop devices.

        """

        if fps is None:
            fps = []

        for index, fp in enumerate(fps):
            fps[index] = fp = os.path.abspath(fp)

            if stat.S_ISBLK(os.stat(fp).st_mode) == 0:
                raise ValueError(f"{fp} is not a device file.")

        args = ["--json", "--output-all", "--list"]

        command = ["sudo", "losetup"]
        command.extend(args)
        command.extend(fps)

        result = subprocess.run(
            command, check=True, capture_output=True, encoding="utf-8"
        ).stdout

        loopdevices = json.loads(result.stdout)

        return loopdevices


class Lsblk(_Shell):
    """Wraps `lsblk` shell command."""

    @_Shell.command
    @staticmethod
    def lookup(*args) -> List[Dict[Any, Any]]:
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

        return json.loads(result.stdout)


class PartProbe(_Shell):
    """Wraps `partprobe` shell command."""

    @_Shell.command
    @staticmethod
    def run(*args):
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
    @staticmethod
    def run(devpath: str, layout: List[Dict[str, Any]]) -> None:
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

        command = ["sudo", "sgdisk"]

        for flag_dict in layout:
            part_num = flag_dict["part_number"]
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
