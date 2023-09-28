#!/usr/bin/env python3

import glob
import json
import logging
import os
import subprocess

log = logging.getLogger(__name__)

def read_config_json(fp: str) -> dict:
    """Return the json data of the file at fp."""

    with open(fp, mode="r", encoding="utf-8") as f:
        return json.load(f)


class _ImageBuilderException(Exception):
    """Generic imagebuilder exception."""


class FoundDevException(_ImageBuilderException):
    """Unexpected device file found."""


class FoundBlockDevException(FoundDevException):
    """Unexpected block device file found."""


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
                    ]
                    fs_label_flag: str
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
        """

        self._cfg = storage

        try:
            self._device = storage_device(self._cfg["disk"])
            log.info('Found device file: %s', device_path)
        except Exception as dev_err:
            log.exception(dev_err)
            raise

        self._partitions = []

    @property
    def partitions(self):
        """ Returns the results of partprobe."""

        if len(self._partitions):
            return self._partitions

        # Might as well update if we have partitions on this image.
        partitions = self._partprobe(self._device)
        if len(partitions):
            self._partitions = partitions

        return self._partitions

    @staticmethod
    def _create_filesystem(
        devpath: str,
        fs_type: str,
        fs_label: str = None,
        fs_label_flag: str = "-l",
        fs_args: list = [],
    ):
        """
        Create a filesystem on a partition.
        """

        mkfs_cmd = [f"mkfs.{fs_type}"]
        mkfs_cmd.extend(fs_args)

        if fs_label is not None:
            mkfs_cmd.extend([fs_label_flag, fs_label])

        subprocess.run(mkfs_cmd, check=True)

    @staticmethod
    def _activate_loop(img_file: str) -> str:
        """Activates a storage image as a loop device."""

        # Check if device is already activated and return that.
        losetup = subprocess.run(
            ["losetup", "--list", "--json"], capture_output=True, check=True
        )
        loopdevices = json.loads(losetup.stdout)["loopdevices"]
        for loopdev in loopdevices:
            if loopdev["back-file"] == img_file:
                log.debug("Found %s already activated.", img_file)
                return loopdev["name"]

        # Activate device.
        subprocess.run(["losetup", "-f", img_file], check=True)

        # Recheck for device and return it now.
        losetup = subprocess.run(
            ["losetup", "--list", "--json"], capture_output=True, check=True
        )
        loopdevices = json.loads(losetup.stdout)["loopdevices"]
        for loopdev in loopdevices:
            if loopdev["back-file"] == img_file:
                log.debug("Activated %s", img_file)
                return loopdev["name"]

        # Something is wrong
        raise MissingBlockDevException(f"Missing loopdevice for {img_file}")

    @staticmethod
    def _partition(devpath: str, layout: list) -> list:
        """
        Partition a disk according to the layout.

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
        if len(partitions):
            raise FoundBlockDevException(f"{devpath} already has partitions! {partitions}")

        partition_cmd = ["sgdisk"]
        for partition, count in enumerate(layout):
            partition.extend([
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
        partition_cmd.append(self._device)

        log.debug("Running %s", partition_cmd)
        subprocess.run(partition_cmd, check=True)

        partitions = self._partprobe(self._device)
        if len(partitions) != len(layout):
            raise MissingBlockDevException(f"Cannot find all partitions for {devpath}!")

        log.info("Created %s on %s", partitions, devpath)
        return partitions

    @staticmethod
    def _partprobe(devpath: str) -> list:
        """
        Probes a device for partitions. Returns a tuple of matching partitions.
        """

        subprocess.run(["partprobe", devpath], check=True)

        lsblk = subprocess.run(
            ["lsblk", "--json", devpath], capture_output=True, check=True
        )
        blockdevs = json.loads(lsblk.stdout)["blockdevices"][0].get("children")
        if blockdevs == None:
            return []

        parts = []

        for block in blockdevs:
            part = os.path.join("/dev", block["name"])
            if not os.path.exists(part):
                raise FileNotFoundError(part)
            parts.append(part)

        return parts

    @staticmethod
    def _storage_device(disk: dict) -> str:
        """
        Return the path to writable storage device.

        Params
        ======
        - disk (dict): A dictionary describing a disk or disk image file.
        """

        dev = disk.get("path", "disk.img")

        # The provided disk is in /dev, which means its a writable device.
        if os.path.commonpath(dev, "/dev") == "/dev":
            return dev

        dev_image_fp = os.path.abspath(dev)

        if os.path.exists(dev_image_fp):
            raise FileExistsError(dev_image_fp)

        subprocess.run(
            ["truncate", "-s", disk["size"], dev_image_fp],
            check=True
        )

        return Storage._activate_loop(dev_image_fp)

    def format(self):
        """Install partitions and filesystems."""


def main():

    cfg = read_config_json("config.json")

if __name__ == "__main__":
    main()