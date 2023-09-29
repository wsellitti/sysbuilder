#!/usr/bin/env python3

"""Install Operating Systems on VM images."""

import json
import logging
import os
import subprocess

log = logging.getLogger(__name__)


class _ImageBuilderException(Exception):
    """Generic imagebuilder exception."""


class FoundDevException(_ImageBuilderException):
    """Unexpected device file found."""


class FoundBlockDevException(FoundDevException):
    """Unexpected block device file found."""


class FoundPartitionException(_ImageBuilderException):
    """Unexpected partitions found on disk."""


class MissingDevException(_ImageBuilderException):
    """Expected device file missing."""


class MissingBlockDevException(MissingDevException):
    """Expected block device missing."""


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

        storage (dict)
        --------------
        {
            disk: {
                path: str,
                size: str,
                ptable: str,
            }
            layout: [
                {
                    start: str,
                    end: str,
                    part_type: str,
                    fs_type: str,
                    fs_label: str,
                    fs_args: [
                        str, str
                    ],
                    fs_label_flag: str,
                    fs_create_command: str,
                    mountpoint: str
                }
                ...
            ]
        }

        - disk (dict): A dictionary representing the disk or disk image to
          capture with the storage object.
        - disk{path} (str): Path to the disk
        - disk{size} (str): Size of the disk image
        - disk{ptable} (str): Partition table type.
        - layout (list): A list of dictionaries, each representing a partition
          on the disk or disk image.
        - layout[{start}] (str): Partition start.
        - layout[{end}] (str): Partition end.
        - layout[{part_type}] (str): Partition type.
        - layout[{fs_type}] (str): Filesystem type. 
        - layout[{fs_label}] (str): Filesystem label.
        - layout[{fs_args}] (list): A list of strings, each item is an
          additional flag used to create a filesystem.
        - layout[{fs_label_flag}] (str): A flag for filesystems that use weird
          flags to label the filesystem.
        - layout[{fs_create_command}] (str): What base command to use to create
          the filesystem.
        - layout[{mountpoint}] (str): Where the filesystem will be mounted in
          the installed system.
        """

        self._cfg = storage

        self._device = self._storage_device(
            img_path=self._cfg["disk"]["path"], size=self._cfg["disk"]["size"]
        )
        log.info('Found device file: %s', self._device)

        self._partitions = []

    @property
    def partitions(self):
        """ Returns the results of partprobe."""

        if self._partitions:
            return self._partitions

        # Might as well update if we have partitions on this image.
        partitions = self._partprobe(self._device)
        if partitions:
            self._partitions = partitions

        return self._partitions

    @staticmethod
    def _activate_loop(img_file: str) -> str:
        """
        Activates a storage image as a loop device, or returns the already
        active loop device.
        """

        log.debug("Checking for loop devices for %s.", img_file)
        # Check if device is already activated and return that.
        losetup = subprocess.run(
            ["losetup", "--list", "--json"], capture_output=True, check=True
        )
        loopdevices = json.loads(losetup.stdout)["loopdevices"]
        for loopdev in loopdevices:
            if loopdev["back-file"] == img_file:
                return loopdev["name"]
        log.debug("%s does not have an active loop device.", img_file)

        # Activate device.
        subprocess.run(["losetup", "-f", img_file], check=True)

        # Recheck for device and return it now.
        losetup = subprocess.run(
            ["losetup", "--list", "--json"], capture_output=True, check=True
        )
        loopdevices = json.loads(losetup.stdout)["loopdevices"]
        for loopdev in loopdevices:
            if loopdev["back-file"] == img_file:
                return loopdev["name"]

        # Something is wrong
        raise MissingBlockDevException(f"Missing loopdevice for {img_file}")

    @staticmethod
    def _create_filesystem(
        devpath: str,
        fs_type: str,
        fs_label: str | None = None,
        fs_label_flag: str = "-L",
        fs_args: list | None = None,
        fs_create_command: str | None = None
    ) -> None:
        """
        Create a filesystem on a partition.
        """

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
    def _deactivate_loop(devpath: str) -> None:
        """Deactivates an active loop device."""

        # Check if device is already activated and return that.
        if not os.path.exists(devpath):
            return

        subprocess.run(["losetup", "-d", devpath], check=True)

    @staticmethod
    def _mount(devpath: str, mountpoint: str) -> None:
        """
        Mount device on mountpoint, creating mountpoint if it does not exist.

        Params
        ======
        - devpath (str): Path to device file in /dev.
        - mountpoint (str): Mountpoint on host filesystem.
        """

    @staticmethod
    def _partition(devpath: str, layout: list) -> list:
        """
        Partition a disk according to what's defined in the layout. Raises
        FoundPartitionException if the disk already has partitions.

        Params
        ======
        - layout (list): A list of dictionaries, each representing a partition
          on the disk or disk image.

        Returns
        =======
        (list) The disks partitions.
        """

        offset = 1 # partition tables start at one but lists start at 0

        partitions = Storage._partprobe(devpath)
        if partitions:
            raise FoundPartitionException(
                f"{devpath} already has partitions! {partitions}"
            )

        partition_cmd = ["sgdisk"]
        for count, partition in enumerate(layout):
            partition_cmd.extend([
                "-n",
                ":".join([
                    str(count + offset),
                    partition["start"],
                    partition["end"]
                ]),
                "-t",
                ":".join([
                    str(count + offset),
                    partition["part_type"]
                ])
            ])
        partition_cmd.append(devpath)

        log.debug("Running %s", partition_cmd)
        subprocess.run(partition_cmd, check=True, capture_output=True)

        log.debug("Probing %s for partitions", devpath)
        partitions = Storage._partprobe(devpath)
        if len(partitions) != len(layout):
            raise MissingBlockDevException(f"Cannot find all partitions for {devpath}!")

        return partitions

    @staticmethod
    def _partprobe(devpath: str) -> list:
        """
        Returns partitions on a device.
        """

        subprocess.run(["partprobe", devpath], check=True)

        lsblk = subprocess.run(
            ["lsblk", "--json", devpath], capture_output=True, check=True
        )
        blockdevs = json.loads(lsblk.stdout)["blockdevices"][0].get("children")
        if blockdevs is None:
            return []

        parts = []

        for block in blockdevs:
            part = os.path.join("/dev", block["name"])
            if not os.path.exists(part):
                raise MissingBlockDevException(part)
            parts.append(part)

        return parts

    @staticmethod
    def _storage_device(img_path: str = "disk.img", size: str = "32G") -> str:
        """
        Return the path to a writable storage device.

        Params
        ======
        - img_path (str): Path to an image file or device file. Defaults to
          "disk.img".
        - size (str): Size of image file. Only used if img_path points to a
          nonexistant file. Defaults to "32G"
        """

        devpath = os.path.abspath(img_path)

        # The provided disk is in /dev, which means its a writable device.
        log.debug("Check if %s is a device file.", devpath)
        if os.path.commonpath([devpath, "/dev"]) == "/dev":
            return devpath
        log.debug("%s is not a device file.", devpath)

        if os.path.exists(devpath):
            raise FileExistsError(devpath)

        subprocess.run(
            ["truncate", "-s", size, devpath],
            check=True
        )

        return Storage._activate_loop(devpath)

    def format(self) -> None:
        """
        Install partitions and filesystems on empty disks.
        """

        self._partitions = self._partition(self._device, self._cfg["layout"])
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
            self._create_filesystem(
                devpath=part,
                fs_args=fs_args,
                fs_label=fs_label,
                fs_label_flag=fs_label_flag,
                fs_type=fs_type,
                fs_create_command=fs_create_command
            )
            log.info("Created %s on %s", fs_type, part)

    def mount(self) -> None:
        """Mount filesystems per configuration."""

def read_config_json(cfg_fp: str) -> dict:
    """Return the json data of the file at fp."""

    with open(cfg_fp, mode="r", encoding="utf-8") as cfg:
        return json.load(cfg)

def main():
    """Main."""

    cfg = read_config_json("config.json")

    vmdisk = Storage(storage=cfg["storage"])
    vmdisk.format()

if __name__ == "__main__":
    main()
