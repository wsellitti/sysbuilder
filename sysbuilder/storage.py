"""Manage storage devices."""

import json
import logging
import os
import subprocess
from typing import List, Dict, Any
from sysbuilder.exceptions import (
    BlockDeviceExistsException,
    BlockDeviceNotFoundException,
)

log = logging.getLogger(__name__)


class _BlockDevice:
    """Linux block device commands."""

    @staticmethod
    def get_child_devices(devpath: str) -> List[Dict[Any, Any]]:
        """Get's child devices."""

        block_dev = _BlockDevice.list_one(devpath=devpath)
        children = []
        for child in block_dev.get("children", []):
            children.append(child["path"])
            children.extend(_BlockDevice.get_child_devices(child["path"]))

        return children

    @staticmethod
    def list_all() -> List[Dict[Any, Any]]:
        """List all block devices."""

        log.debug("Checking for block devices.")
        lsblk = subprocess.run(
            ["lsblk", "-O", "--json"],
            capture_output=True,
            check=True,
            encoding="utf-8",
        ).stdout
        block_devices = json.loads(lsblk)["blockdevices"]

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
                    encoding="utf-8"
                ) as f:
                    dev["back-file"] = f.read()

        return block_devices

    @staticmethod
    def list_one(devpath: str) -> Dict[Any, Any]:
        """List one block device."""

        log.debug("Checking for block device: %s.", devpath)

        if not os.path.exists(devpath):
            raise BlockDeviceNotFoundException

        lsblk = subprocess.run(
            ["lsblk", "-O", "--json", devpath],
            capture_output=True,
            check=True,
            encoding="utf-8",
        ).stdout
        dev = json.loads(lsblk)["blockdevices"][0]

        # For whatever reason this was removed in a recent version of lsblk
        if dev["type"] == "loop":
            if "back-file" not in dev:
                with open(
                    os.path.join(
                        ["/sys", "block", dev["name"], "loop", "backing_file"]
                    ),
                    mode="r",
                    encoding="utf-8"
                ) as f:
                    dev["back-file"] = f.read()

        return dev

    @staticmethod
    def partition(devpath: str, layout: list) -> list:
        """
        Partition a disk according to what's defined in the layout. Raises
        BlockDeviceExistsException if the disk already has partitions.

        Params
        ======
        - layout (list): A list of dictionaries, each representing a partition
          on the disk or disk image.

        Returns
        =======
        (list) The disks partitions.
        """

        offset = 1  # partition tables start at one but lists start at 0

        partitions = _BlockDevice.partprobe(devpath)
        if partitions:
            raise BlockDeviceExistsException(
                f"{devpath} already has partitions! {partitions}"
            )

        partition_cmd = ["sgdisk"]
        for count, partition in enumerate(layout):
            partition_cmd.extend(
                [
                    "-n",
                    ":".join(
                        [
                            str(count + offset),
                            partition["start"],
                            partition["end"],
                        ]
                    ),
                    "-t",
                    ":".join([str(count + offset), partition["part_type"]]),
                ]
            )
        partition_cmd.append(devpath)

        log.debug("Running %s", partition_cmd)
        subprocess.run(
            partition_cmd, check=True, capture_output=True, encoding="utf-8"
        )

        log.debug("Probing %s for partitions", devpath)
        partitions = _BlockDevice.partprobe(devpath)
        if len(partitions) != len(layout):
            raise BlockDeviceNotFoundException(
                f"Cannot find all partitions for {devpath}!"
            )

        return partitions

    @staticmethod
    def partprobe(devpath: str) -> list:
        """
        Returns partitions on a device.
        """

        subprocess.run(["partprobe", devpath], check=True)

        blockdevs = _BlockDevice.list_one(devpath=devpath).get("children")
        if blockdevs is None:
            return []

        parts = []

        for block in blockdevs:
            part = os.path.join("/dev", block["name"])
            if not os.path.exists(part):
                raise BlockDeviceNotFoundException(part)
            parts.append(part)

        return parts


class _VirtualDiskImage:
    """Disk image file commands."""

    @staticmethod
    def activate(img_file: str) -> str:
        """
        Activates a storage image as a loop device, or returns the already
        active loop device.
        """

        loopdevices = _BlockDevice.list_all()
        for loopdev in loopdevices:
            if loopdev["back-file"] == img_file:
                return loopdev["name"]
        log.info("%s does not have an active loop device.", img_file)

        # Activate device.
        log.debug("Run %s", ["losetup", "-f", img_file])
        subprocess.run(["losetup", "-f", img_file], check=True)

        # Recheck for device and return it now.
        loopdevices = _BlockDevice.list_all()
        for loopdev in loopdevices:
            if loopdev["back-file"] == img_file:
                return loopdev["name"]

        # Something is wrong
        raise BlockDeviceNotFoundException(f"Missing loopdevice for {img_file}")

    @staticmethod
    def create(img_path: str = "disk.img", size: str = "32G") -> str:
        """
        Create a disk image file, activate it as a loop device, and return the
        path to the loop device.

        Params
        ======
        - img_path (str): Path to an image file or device file. Defaults to
          "disk.img".
        - size (str): Size of image file. Only used if img_path points to a
          nonexistant file. Defaults to "32G"

        Returns
        =======
        (str) The path to the loop device.
        """

        devpath = os.path.abspath(img_path)

        # The provided disk is in /dev, which means its a writable device.
        log.debug("Check if %s is a device file.", devpath)
        if os.path.commonpath([devpath, "/dev"]) == "/dev":
            return devpath
        log.debug("%s is not a device file.", devpath)

        if os.path.exists(devpath):
            raise FileExistsError(devpath)

        subprocess.run(["truncate", "-s", size, devpath], check=True)

        return _VirtualDiskImage.activate(devpath)

    @staticmethod
    def deactivate(devpath: str) -> None:
        """Deactivates an active loop device."""

        # Check if device is already activated and return that.
        loopdev = _BlockDevice.list_one(devpath=devpath)

        if loopdev["type"] != "loop":
            raise ValueError(f"{devpath} is not a loop device!")

        subprocess.run(["losetup", "-d", devpath], check=True)

    @staticmethod
    def find_active_devices(path: str) -> List[str]:
        """
        Find active _BlockDevs and _FileSystems using `path` as a backing
        file.
        """

        loopdevs = _BlockDevice.list_all()
        active_devices = []
        for dev in loopdevs:
            if (dev["type"] == "loop" and dev["back-file"] == path):
                active_devices.append(dev["path"])

        return active_devices

class _FileSystem:
    """Linux part device commands."""

    @staticmethod
    def create(
        devpath: str,
        fs_type: str,
        fs_label: str | None = None,
        fs_label_flag: str = "-L",
        fs_args: list | None = None,
        fs_create_command: str | None = None,
    ) -> None:
        """
        Create a filesystem on a partition.
        """

        if not os.path.exists(devpath):
            raise BlockDeviceNotFoundException

        if fs_args is None:
            fs_args = []

        if fs_create_command is None:
            fs_create_command = f"mkfs.{fs_type}"

        mkfs_cmd = [fs_create_command]
        mkfs_cmd.extend(fs_args)
        if fs_label is not None:
            mkfs_cmd.extend([fs_label_flag, fs_label])
        mkfs_cmd.append(devpath)

        log.debug("Running %s", mkfs_cmd)
        subprocess.run(mkfs_cmd, check=True)

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

        subprocess.run(
            ["mount", devpath, mountpoint],
            check=True,
            capture_output=True,
            encoding="utf-8",
        )

    @staticmethod
    def unmount(devpath: str) -> None:
        """
        Unmount a device.

        Params
        ======
        - devpath (str): Device path.
        """

        if not os.path.exists(devpath):
            raise BlockDeviceNotFoundException(devpath)


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

        self._device = _VirtualDiskImage.create(
            img_path=self._cfg["disk"]["path"], size=self._cfg["disk"]["size"]
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
        """

        self._partitions = _BlockDevice.partition(
            self._device, self._cfg["layout"]
        )
        log.info(
            "Created partitions for %s: %s", self._device, self._partitions
        )

        for count, part in enumerate(self._partitions):
            filesystem_descriptor = self._cfg["layout"][count]
            fs_type = filesystem_descriptor["fs_type"]
            fs_label = filesystem_descriptor.get("fs_label")
            fs_label_flag = filesystem_descriptor.get("fs_label_flag", "-L")
            fs_args = filesystem_descriptor.get("fs_args")
            fs_create_command = filesystem_descriptor.get("fs_create_command")
            _FileSystem.create(
                devpath=part,
                fs_args=fs_args,
                fs_label=fs_label,
                fs_label_flag=fs_label_flag,
                fs_type=fs_type,
                fs_create_command=fs_create_command,
            )
            log.info("Created %s on %s", fs_type, part)

    def mount(self) -> None:
        """Mount filesystems per configuration."""
