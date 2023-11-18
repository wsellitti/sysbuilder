"""Shell commands."""

import json
import logging
import os
import stat
import subprocess
from typing import Any, Dict, List

log = logging.getLogger(__name__)


class _Shell:
    """Generic _Shell class."""

    @staticmethod
    def run(cmd: List["str"]) -> str:
        """
        Run the command `cmd` and return what's printed to stdout.
        """

        log.debug(cmd)
        result = subprocess.run(
            cmd, capture_output=True, check=True, encoding="utf-8"
        )

        return result.stdout


class DD(_Shell):
    """Wraps `dd` shell command."""

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


class Mkfs(_Shell):
    """
    mkfs wrapper
    """

    @staticmethod
    def create(
        devpath: str,
        fstype: str,
        fs_label: str | None = None,
        fs_label_flag: str = "-L",
        fs_args: List[str] | None = None,
    ) -> None:
        """
        mkfs wrapper
        """

        blockdev = Lsblk.lookup(devpath)  # Block device check

        if blockdev["fstype"] is not None:
            raise FileExistsError(
                f"{blockdev['fstype']} detected on {devpath}!"
            )

        args = ["--type", fstype]
        args.extend([] if fs_label is None else [fs_label_flag, fs_label])
        args.extend([] if fs_args is None else fs_args)

        command = ["sudo", "mkfs"]
        command.extend(args)
        command.append(devpath)

        subprocess.run(
            command, check=True, capture_output=True, encoding="utf-8"
        )


class PartProbe(_Shell):
    """Wraps `partprobe` shell command."""

    @staticmethod
    def probe_device(devpath: str):
        """Probes a device `devpath` for partitions."""

        if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
            raise ValueError(f"{devpath} is not a device file.")

        command = ["sudo", "partprobe"]
        command.append(devpath)

        PartProbe.run(command)


class SGDisk(_Shell):
    """Wraps `sgdisk` shell command."""

    @staticmethod
    def create_partition(
        devpath: str,
        part_number: str,
        start_sector: str = "",
        end_sector: str = "",
    ) -> None:
        """
        Use sgdisk to create a partition.

        # Params

          - devpath (str): Path to the device.
          - part_number (str): The partition number. This should be a nonzero
            integer in a string.
          - start_sector (str): The on-disk sector a partition should start
            at. This can be an absolute sector number or a relative value
            measured in kibibytes, mebibytes, gibibytes, tebibytes, or
            prebibytes.
          - end_sector (str): The on-disk sector a partition should end at.
            This can be an absolute sector number or a relative value measured
            in kibibytes, mebibytes, gibibytes, tebibytes, or prebibytes.
        """

        if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
            raise ValueError(f"{devpath} is not a device file.")

        command = ["sudo", "sgdisk"]

        args = [
            "--new",
            ":".join([part_number, str(start_sector), str(end_sector)]),
        ]

        command.extend(args)
        command.append(devpath)

        SGDisk.run(command)

    @staticmethod
    def set_partition_type(
        devpath: str, part_number: str, typecode: str
    ) -> None:
        """
        Use sgdisk to assign a typecode to a partition.

        # Params

          - devpath (str): Path to the device.
          - part_number (int): The partition number. This should be a nonzero
            integer in a string.
          - typecode (str): A 4-character hexadecimal value representing
            filesystem type codes.
        """

        if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
            raise ValueError(f"{devpath} is not a device file.")

        command = ["sudo", "sgdisk"]

        args = [
            "--typecode",
            ":".join([part_number, typecode]),
        ]

        command.extend(args)
        command.append(devpath)

        SGDisk.run(command)
