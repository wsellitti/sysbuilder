"""Manage storage devices."""

import json
import logging
import os
import subprocess
from typing import List, Dict, Any
from sysbuilder.exceptions import (
    BlockDeviceNotFoundError,
    BlockDeviceError,
    FileSystemError,
    LoopDeviceError,
)

log = logging.getLogger(__name__)


class _BlockDevice:
    """Linux block device commands."""

    @staticmethod
    def is_disk(devpath: str) -> bool:
        """Return true if the block device a disk device."""
        return _BlockDevice.list_one(devpath=devpath)["type"] == "disk"

    @staticmethod
    def is_loop(devpath: str) -> bool:
        """Return true if the block device a loop device."""
        return _BlockDevice.list_one(devpath=devpath)["type"] == "loop"

    @staticmethod
    def is_part(devpath: str) -> bool:
        """Return true if the block device a disk partition."""
        return _BlockDevice.list_one(devpath=devpath)["type"] == "part"

    # Find block devices

    @staticmethod
    def get_child_devices(devpath: str, depth: int = -1) -> List[str]:
        """
        Get's child devices.

        Params
        ======
        - devpath: Device path.
        - depth: How many layers of children to go to. Proving a negative
          number means go forever.

        Returns
        =======
        (list) Block device paths.
        """

        block_dev = _BlockDevice.list_one(devpath=devpath)
        children = []
        if depth != 0:
            for child in block_dev.get("children", []):
                children.append(child["path"])
                children.extend(
                    _BlockDevice.get_child_devices(
                        child["path"], depth=(depth - 1)
                    )
                )

        return children

    @staticmethod
    def list_all() -> List[Dict[Any, Any]]:
        """List all block devices."""

        try:
            lsblk = subprocess.run(
                ["lsblk", "--output-all", "--json"],
                capture_output=True,
                check=True,
                encoding="utf-8",
            ).stdout
        except subprocess.CalledProcessError as lsblk_error:
            if lsblk_error.returncode == 64:
                raise BlockDeviceError(
                    "Unable to retrieve block devices."
                ) from lsblk_error
            raise

        try:
            block_devices = json.loads(lsblk)["blockdevices"]
        except json.JSONDecodeError as json_err:
            raise BlockDeviceError(
                "Unable to retrieve block devices."
            ) from json_err

        # For whatever reason this was removed in a recent version of lsblk
        for dev in block_devices:
            if dev["type"] == "loop":
                if "back-file" in dev:
                    continue
                with open(
                    os.path.join(
                        ["/sys", "block", dev["name"], "loop", "backing_file"]
                    ),
                    mode="r",
                    encoding="utf-8",
                ) as f:  # pylint: disable=C0103
                    dev["back-file"] = f.read()

        return block_devices

    @staticmethod
    def list_one(devpath: str) -> Dict[Any, Any]:
        """List one block device."""

        try:
            lsblk = subprocess.run(
                ["lsblk", "--output-all", "--json", devpath],
                capture_output=True,
                check=True,
                encoding="utf-8",
            ).stdout
        except subprocess.CalledProcessError as lsblk_error:
            if lsblk_error.returncode == 32:
                raise BlockDeviceNotFoundError(devpath) from lsblk_error
            raise

        try:
            dev = json.loads(lsblk)["blockdevices"][0]
        except json.JSONDecodeError as json_err:
            raise BlockDeviceError(f"Cannot find {devpath}") from json_err

        # For whatever reason this was removed in a recent version of lsblk
        if dev["type"] == "loop":
            if "back-file" not in dev:
                with open(
                    os.path.join(
                        ["/sys", "block", dev["name"], "loop", "backing_file"]
                    ),
                    mode="r",
                    encoding="utf-8",
                ) as f:  # pylint: disable=C0103
                    dev["back-file"] = f.read()

        return dev

    # Manipulate block devices

    @staticmethod
    def create_partition(
        devpath: str,
        start_sector: str = "",
        end_sector: str = "",
        typecode: str = "ef00",
    ) -> None:
        """
        Partition a disk according to what's defined in the layout. Raises
        BlockDeviceExistsError if the disk already has partitions.

        Params
        ======
        - devpath (list): The device path.
        - start_sector (str): Sector where the partition should start. Values
          can be absolute or positions measured in standard notation: "K",
          "M", "G", "T". Providing and empty string "" will use the next
          available starting sector. Values beginning with a "+" will start
          the parittion that distance past the next available starting sector
          (ie, "+2G" will cause the next partition to start 2 gibibytes after
          the last partition ended). Values beginning with a "-"  will start
          the partition that distance from the next available ending sector
          with enough space (ie, "-2G" will create a partition that starts 2
          gibibytes before the ending most available sector).
        - end_sector (str): Sector where the partition should end. Values can
          be absolute or positions measured in standard notation: "K", "M",
          "G", "T". Providing and empty string "" will use the next available
          ending sector from the starting sector. Values beginning with a "+"
          will end the partition that distance past the starting sector (ie,
          "+2G" will create a 2 gibibyte partition). Values beginning with a
          "-" will end the partition that distance from the next available
          ending sector (ie, "-2G" will create a partition that 2 gibibytes
          short of the maximum space available for that partiton).
        - typecode (str): A 4-digit hexadecimal value representing partition
          type codes, as returned from `sgdisk -L`.
        """

        old_partitions = _BlockDevice.partprobe(devpath)

        count = str(len(old_partitions))

        try:
            subprocess.run(
                [
                    "sgdisk",
                    "--new",
                    ":".join([count, str(start_sector), str(end_sector)]),
                    "--typecode",
                    ":".join([count, typecode]),
                ],
                check=True,
                capture_output=True,
                encoding="utf-8",
            )
        except subprocess.CalledProcessError as part_err:
            raise BlockDeviceError(
                f"Cannot create partition {count} on {devpath}!"
            ) from part_err

    @staticmethod
    def get_partitions(devpath: str) -> List[str]:
        """
        Returns a list of partitions. Raises ValueError if `devpath` is not a
        disk device
        """

        if _BlockDevice.is_disk(devpath=devpath):
            raise ValueError(f"{devpath} is not a disk!")

        return _BlockDevice.get_child_devices(devpath=devpath, depth=1)

    @staticmethod
    def partprobe(devpath: str) -> None:
        """
        Raises BlockDeviceError.
        """

        try:
            subprocess.run(
                ["partprobe", devpath], check=True, capture_output=True
            )
        except subprocess.CalledProcessError as probe_err:
            raise BlockDeviceError(
                f"Unable to probe {devpath} for partitions."
            ) from probe_err


class _FileSystem:
    """Linux part device commands."""

    @staticmethod
    def create(
        devpath: str,
        fs_type: str,
        fs_label: str | None = None,
        fs_label_flag: str = "-L",
        fs_args: list | None = None,
    ) -> None:
        """
        Create a filesystem on a partition.
        """

        blockdev = _BlockDevice.list_one(devpath=devpath)

        if blockdev["fstype"] is not None:
            raise FileExistsError(f"{blockdev['fstype']} detected on {devpath}")

        mkfs_cmd = ["mkfs", "--type", fs_type]
        if fs_type == "swap":
            mkfs_cmd = ["mkswap"]

        mkfs_cmd.extend([] if fs_label is None else [fs_label_flag, fs_label])

        mkfs_cmd.extend([] if fs_args is None else fs_args)

        mkfs_cmd.append(devpath)

        try:
            subprocess.run(mkfs_cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as mkfs_err:
            raise FileSystemError(
                f"Cannot create {fs_type} on {devpath}"
            ) from mkfs_err

    @staticmethod
    def mount(devpath: str, mountpoint: str) -> None:
        """
        Mount device on mountpoint, creating mountpoint if it does not exist.

        Params
        ======
        - devpath (str): Path to device file in /dev.
        - mountpoint (str): Mountpoint on host filesystem.
        """

        if not (os.path.exists(mountpoint) and os.path.isdir(mountpoint)):
            raise FileNotFoundError(mountpoint)

        # Make sure device isn't already mounted there.
        mountpoints = _BlockDevice.list_one(devpath=devpath).get(
            "mountpoints", []
        )
        for existing_mount in mountpoints:
            if existing_mount == mountpoint:
                return

        try:
            subprocess.run(
                ["mount", devpath, mountpoint],
                check=True,
                capture_output=True,
                encoding="utf-8",
            )
        except subprocess.CalledProcessError as mount_err:
            raise FileSystemError(
                f"Cannot mount {devpath} on {mountpoint}"
            ) from mount_err

    @staticmethod
    def unmount_all_mounts(devpath: str) -> None:
        """
        Unmount a device.

        Params
        ======
        - devpath (str): Device path.
        """

        # Make sure device isn't already mounted there.
        mountpoints = _BlockDevice.list_one(devpath=devpath).get(
            "mountpoints", []
        )
        for existing_mount in mountpoints:
            try:
                subprocess.run(
                    ["unmount", existing_mount], check=True, capture_output=True
                )
            except subprocess.CalledProcessError as unmount_err:
                raise FileSystemError(
                    f"Cannot unmount {devpath} from {existing_mount}."
                ) from unmount_err


class _LoopDevice:
    """
    Loop device specific commands, once activated loop devices behave like
    block devices.
    """

    @staticmethod
    def attach(path: str) -> str:
        """
        Activates a storage image as a loop device, or returns the already
        active loop device.
        """

        path = os.path.abspath(path)

        try:
            return subprocess.run(
                [
                    "losetup",
                    "--show",
                    "--find",
                    "--nooverlap",
                    "--partscan",
                    path,
                ],
                check=True,
                capture_output=True,
                encoding="utf-8",
            ).stdout
        except subprocess.CalledProcessError as losetup_err:
            raise LoopDeviceError(f"Cannot attach {path}") from losetup_err

    @staticmethod
    def detach(devpath: str) -> None:
        """Deactivates an active loop device."""

        devpath = os.path.abspath(devpath)

        try:
            subprocess.run(
                ["losetup", "--detach", devpath],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as losetup_err:
            raise LoopDeviceError(f"Cannot detach {devpath}") from losetup_err

    @staticmethod
    def detach_all() -> None:
        """Deactivate all active loop devices."""

        try:
            subprocess.run(
                ["losetup", "--detach-all"], check=True, capture_output=True
            )
        except subprocess.CalledProcessError as losetup_err:
            raise LoopDeviceError("Cannot detach all devices.") from losetup_err

    @staticmethod
    def list_one(devpath: str) -> Dict[Any, Any]:
        """Get details for one loop device."""

        try:
            losetup = subprocess.run(
                ["losetup", "--json", "--output-all", devpath],
                check=True,
                capture_output=True,
                encoding="utf-8",
            ).stdout
        except subprocess.CalledProcessError as losetup_err:
            raise LoopDeviceError(
                "Cannot query loopback devices!"
            ) from losetup_err

        try:
            return json.loads(losetup)["loopdevices"][0]
        except json.JSONDecodeError as json_err:
            raise LoopDeviceError(
                "Cannot query loopback devices!"
            ) from json_err

    @staticmethod
    def list_all() -> List[Dict[Any, Any]]:
        """Return all loop devices."""

        try:
            losetup = subprocess.run(
                ["losetup", "--json", "--output-all", "--list"],
                capture_output=True,
                check=True,
                encoding="utf-8",
            ).stdout
        except subprocess.CalledProcessError as losetup_err:
            if losetup_err.returncode == 64:
                raise LoopDeviceError(
                    "Cannot query loopback devices!"
                ) from losetup_err
            raise

        try:
            return json.loads(losetup)["loopdevices"]
        except json.JSONDecodeError as json_err:
            raise LoopDeviceError(
                "Cannot query loopback devices!"
            ) from json_err

    # Virtual Disk Image Specific functions ---

    @staticmethod
    def create(path: str, size: str = "32G") -> str:
        """
        Create a disk image file, activate it as a loop device, and return the
        path to the loop device.

        Params
        ======
        - path (str): Path to an image file or device file.
        - size (str): Size of image file. Only used if path points to a
          nonexistant file. Defaults to "32G"

        Returns
        =======
        (str) The path to the loop device.
        """

        devpath = os.path.abspath(path)

        if os.path.exists(devpath):
            raise FileExistsError(devpath)

        subprocess.run(
            ["truncate", "--size", size, devpath],
            check=True,
            capture_output=True,
        )

        return _LoopDevice.attach(devpath)

    @staticmethod
    def list_associated(path: str) -> List[str]:
        """
        Find active virtual disk block devices using the disk image as
        background storage.
        """

        devices = []

        try:
            losetup = subprocess.run(
                ["losetup", "--associated", path],
                check=True,
                capture_output=True,
                encoding="utf-8",
            ).stdout
        except subprocess.CalledProcessError as losetup_err:
            raise LoopDeviceError(
                "Cannot query loopback devices"
            ) from losetup_err

        if losetup == "":
            return []

        for line in losetup.split("\n"):
            devpath = line.split(":")[0]
            devices.append(_LoopDevice.list_one(devpath=devpath))

        return devices


class Storage:
    """
    A storage object representing a storage device, real or image file.
    """

    def __init__(self, storage: dict):
        """
        Storage object.

        Params
        ======
        - storage (dict): A dictionary representing a device and it's partition
          layout.
        """

        self._cfg = storage

        self._device = _LoopDevice.create(
            path=self._cfg["disk"]["path"], size=self._cfg["disk"]["size"]
        )
        log.info("Found device file: %s", self._device)

        self._partitions = []

    @property
    def partitions(self):
        """Returns the results of partprobe."""

        if self._partitions:
            return self._partitions

        # Might as well update if we have partitions on this image.
        partitions = _BlockDevice.partprobe(self._device)
        if partitions:
            self._partitions = partitions

        return self._partitions

    def format(self) -> None:
        """
        Install partitions and filesystems on empty disks.

        As each partition is created check self._device for all partitions,
        and configure the first one without a filesystem with the filesystem
        defined in the layout. As filesystems are being created sequentially
        to partitions, the first partition without a filesystem should always
        been the one created previously. Once a filesystem is created mount it
        as per the layout.

        Admittedly this process is susceptible to race conditions if two (or
        more) partitions were to be created (nearly) simultaneously. As long
        as the partitions are created in the order they should be in on the
        disk they will be processed correctly.
        """

        for part in self._cfg["layout"]:
            _BlockDevice.create_partition(
                devpath=self._device["path"],
                start_sector=part["start"],
                end_sector=part["end"],
                typecode=part["typecode"],
            )

            fs_cfg = part["filesystem"]

            # This probably isn't necessary but it shouldn't hurt.
            _BlockDevice.partprobe(self._device)

            for tmp in _BlockDevice.get_partitions(self._device):
                if tmp.get("fstype") is None:
                    _FileSystem.create(
                        devpath=tmp["path"],
                        fs_type=fs_cfg["fs_type"],
                        fs_args=fs_cfg.get("args"),
                        fs_label=fs_cfg.get("label"),
                        fs_label_flag=fs_cfg.get("label_flag", "-L"),
                    )

                    _FileSystem.mount(
                        devpath=tmp["devpath"], mountpoint=fs_cfg["mountpoint"]
                    )

            self._partitions = _BlockDevice.get_partitions(self._device)

    def mount(self) -> None:
        """Mount filesystems per configuration."""
