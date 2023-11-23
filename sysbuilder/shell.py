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
    def write_file(
        input_file: str,
        output_file: str,
        count: str,
        bs: str = "1M",
        convs: List[str] | None = None,
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

        DD.run(command)


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

        output = Losetup.run(command)

        log.debug("%s created successfully", output)

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

        Losetup.run(command)

        try:
            Lsblk.list_one(fp)
            raise FileExistsError(fp)
        except subprocess.CalledProcessError:
            log.debug("%s removed successfully", fp)

    @staticmethod
    def detach_all() -> None:
        """
        Wraps losetup.

        For deactivating all loop devices.
        """

        args = ["--detach-all"]

        command = ["sudo", "losetup"]
        command.extend(args)

        Losetup.run(command)

    @staticmethod
    def identify(fp: str) -> str:
        """
        Wraps losetup.

        Finds which loop device is backed by the file `fp`.
        """

        fp = os.path.abspath(fp)

        if not os.path.exists(fp):
            raise ValueError(f"{fp} does not exist!")

        args = ["--find", "--show", "--nooverlap"]

        command = ["sudo", "losetup"]
        command.extend(args)
        command.append(fp)

        output = Losetup.run(command)

        return output.strip()

    @staticmethod
    def list_one(devpath: str) -> Dict[str, List[Dict[Any, Any]]]:
        """
        Gets details for a loop device `devpath`.
        """

        devpath = os.path.abspath(devpath)

        if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
            raise ValueError(f"{devpath} is not a device file.")

        args = ["--json", "--output-all", "--list"]

        command = ["sudo", "losetup"]
        command.extend(args)
        command.append(devpath)

        output = Losetup.run(command)

        loopdevices = json.loads(output)

        return loopdevices

    @staticmethod
    def list_many(devpaths: List[str]) -> Dict[str, List[Dict[Any, Any]]]:
        """
        Gets details for loop devices `devpaths`.
        """

        for index, devpath in enumerate(devpaths):
            devpaths[index] = devpath = os.path.abspath(devpath)

            if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
                raise ValueError(f"{devpath} is not a device file.")

        args = ["--json", "--output-all", "--list"]

        command = ["sudo", "losetup"]
        command.extend(args)
        command.extend(devpaths)

        output = Losetup.run(command)

        loopdevices = json.loads(output)

        return loopdevices


class Lsblk(_Shell):
    """Wraps `lsblk` shell command."""

    @staticmethod
    def list_all() -> Dict[str, List[Dict[Any, Any]]]:
        """
        Get details about all block devices.
        """

        command = ["lsblk", "--output-all", "--json"]
        output = Lsblk.run(command)
        return json.loads(output)

    @staticmethod
    def list_one(devpath: str) -> Dict[str, List[Dict[Any, Any]]]:
        """
        Get details about the block device `devpath`.
        """

        if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
            raise ValueError(f"{devpath} is not a device file.")

        command = ["lsblk", "--output-all", "--json"]
        command.append(devpath)

        output = Lsblk.run(command)

        return json.loads(output)

    @staticmethod
    def list_multiple(devpaths: List[str]) -> Dict[str, List[Dict[Any, Any]]]:
        """
        Get details about the block devices in `devpaths`.
        """

        for devpath in devpaths:
            if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
                raise ValueError(f"{devpath} is not a device file.")

        command = ["lsblk", "--output-all", "--json"]
        command.extend(devpaths)

        output = Lsblk.run(command)

        return json.loads(output)


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

        lsblk = Lsblk.list_one(devpath)
        blockdev = lsblk["blockdevices"][0]  # Block device check

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

        Mkfs.run(command)


class Mkswap(_Shell):
    """mkswap wrapper"""

    @staticmethod
    def create(
        devpath: str,
        fs_label: str | None = None,
        fs_args: List[str] | None = None,
    ):
        """
        Make a swap area.

        Usage is nearly identical to `shell.Mkfs.create()`.
        """

        lsblk = Lsblk.list_one(devpath)
        blockdev = lsblk["blockdevices"][0]  # Block device check

        if blockdev["fstype"] is not None:
            raise FileExistsError(
                f"{blockdev['fstype']} detected on {devpath}!"
            )

        command = ["sudo", "mkswap"]

        args = []
        args.extend([] if fs_label is None else ["-L", fs_label])
        args.extend([] if fs_args is None else fs_args)

        command.extend(args)
        command.append(devpath)

        Mkswap.run(command)


class Mount(_Shell):
    """Wraps mount."""

    @staticmethod
    def mount(
        devpath: str,
        mountpoint: str,
        options: List[str] | None = None,
    ) -> None:
        """Mount `devpath` of type `fstype` at `mountpoint` with `options`."""

        command = ["sudo", "mount"]

        args = [devpath, mountpoint]
        if options is not None:
            args.extend({"-o", ",".join(options)})

        command.extend(args)

        Mount.run(command)

    @staticmethod
    def list_all() -> List[Dict[str, str]]:
        """Return a list of dictionaries describing mounts"""


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


class Umount(_Shell):
    """Wraps umount."""

    @staticmethod
    def umount(mountpoint: str) -> None:
        """Unmount `mountpoint`."""

        Umount.run(["sudo", "umount", mountpoint])
