"""
Manage storage devices.

*Nix-based and *Nix-like systems are not object-oriented as much as
file-oriented. In an attempt to reduce the complexity of individual functions
the protected classes in this module represent interactions with file and
file-like objects through the host and various shell commands, organized into
classes largely based on kind of file being manipulated. The public classes
are object-oriented, and call the protected classes as needed.
"""

import logging
import os
import time
import tempfile
from typing import Any, Dict, List, Tuple
from sysbuilder.shell import (
    DD,
    Lsblk,
    Losetup,
    Mkfs,
    Mkswap,
    Mount,
    PartProbe,
    SGDisk,
    Umount,
)
from sysbuilder.exceptions import BlockDeviceError, LoopDeviceNotFoundError

log = logging.getLogger(__name__)


class BlockDevice:
    """
    Block Device represents an actual block device in /dev.
    """

    def __init__(self) -> None:
        """Create block device."""

        self._data = {}
        self._children = []

    def __eq__(self, other) -> bool:
        """Compare self to other."""

        if not isinstance(other, BlockDevice):
            return False

        if other.back_path == self.back_path:
            return True

        return False

    @classmethod
    def from_device_path(cls, devpath: str):
        """JSON from lsblk becomes a BlockDevice."""

        dev = Lsblk.list_one(devpath)["blockdevices"][0]

        blockdev = cls()
        blockdev.update(dev)

        return blockdev

    @classmethod
    def from_all_devices(cls) -> List:
        """JSON from lsblk becomes a list of BlockDevices."""

        devs = Lsblk.list_all()["blockdevices"]
        blockdevs = []
        for dev in devs:
            blockdev = cls()
            blockdev.update(dev)
            blockdevs.append(blockdev)

        return blockdevs

    @classmethod
    def as_image_file(cls, path: str, size: str = "32G"):
        """Create a block device from an image file."""

        if size.endswith("M") or size.endswith("m"):
            msize = int(size[:-1])
        elif size.endswith("G") or size.endswith("g"):
            msize = int(size[:-1]) * 1024
        elif size.endswith("T") or size.endswith("t"):
            msize = int(size[:-1]) * 1024 * 1024
        elif size.endswith("P") or size.endswith("p"):
            msize = int(size[:-1]) * 1024 * 1024 * 1024

        DD.write_file(
            input_file="/dev/zero",
            output_file=path,
            count=str(msize),
            convs=["sparse"],
        )
        Losetup.attach(path)
        loopdev = Losetup.identify(path)
        blockdev = cls.from_device_path(devpath=loopdev)

        loop_attr = Losetup.list_one(loopdev)["loopdevices"][0]
        blockdev.update(loop_attr)

        return blockdev

    @property
    def back_path(self) -> str:
        """
        Returns the backing file for loop devices and the device path for
        physical devices.
        """
        if self.devtype == "loop":
            return self._data["back-file"]
        return self._data["path"]

    @property
    def children(self) -> Tuple:
        """Write protect the list of children (the children can still be updated)."""
        return tuple(self._children)

    @property
    def devtype(self) -> str:
        """Return device type."""
        return self._data["type"]

    @property
    def path(self) -> str:
        """Return the device path."""
        return self._data["path"]

    def add_filesystem(
        self,
        fs_type: str,
        fs_label: str | None = None,
        fs_label_flag: str = "-L",
        fs_args: List[str] | None = None,
    ) -> None:
        """
        Format partitions

        # Params
          - fs_type (str): The filesystem type.
          - fs_label (str): The filesystem label.
          - fs_label_flag (str): The flag used to provide the filesystem label
            to mkfs.
          - fs_args (list): Additional arguments for mkfs.
        """

        if self.get("fstype") is not None:
            raise BlockDeviceError(
                f"Cannot format a formatted block device: {self.path}."
            )

        if fs_type == "swap":
            Mkswap.create(devpath=self.path, fs_label=fs_label, fs_args=fs_args)
        else:
            Mkfs.create(
                devpath=self.path,
                fstype=fs_type,
                fs_args=fs_args,
                fs_label=fs_label,
                fs_label_flag=fs_label_flag,
            )

        self.sync()

    def add_part(  # pylint: disable=R0913
        self,
        start: str,
        end: str,
        typecode: str,
        fs_type: str | None = None,
        fs_label: str | None = None,
        fs_label_flag: str = "-L",
        fs_args: List[str] | None = None,
        install_filesystem: bool = True,
    ) -> None:
        """
        Add partitions to a disk. If `install_filesystem` is true then
        `fs_type`, `fs_label`, `fs_label_flag`, and `fs_args` will be provided
        to the `add_filesystem` function for that partition.

        # Params

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
          - fs_type (str): The filesystem type.
          - fs_label (str): The filesystem label.
          - fs_label_flag (str): The flag used to provide the filesystem label
            to mkfs.
          - fs_args (list): Additional arguments for mkfs.
          - install_filesystem (bool): If `true` call `iinstall_filesystem` on
            the new partition.
        """

        if self.devtype not in ["disk", "loop"]:
            raise BlockDeviceError("Only disks may be partitioned.")

        part_number = len(self._children) + 1

        self.insert_partition(
            part_number=part_number, start=start, end=end, typecode=typecode
        )

        if install_filesystem:
            if fs_type is None:
                raise ValueError(
                    "`fs_type` cannot be None if `install_filesystem` is True."
                )
            self._children[part_number - 1].add_filesystem(
                fs_type=fs_type,
                fs_args=fs_args,
                fs_label=fs_label,
                fs_label_flag=fs_label_flag,
            )

    def close(self) -> None:
        """Deactivate the loopback device if self.devtype is "loop"."""

        if self.devtype != "loop":
            raise LoopDeviceNotFoundError(f"{self.path} is not a loop device!")

        Losetup.detach(fp=self.path)

    def get(self, val, default=None) -> Any:
        """
        Return the value `val` from `self._data`, or the default value
        `default` if `val` is not present.
        """
        return self._data.get(val, default)

    def insert_partition(
        self,
        part_number: int,
        start: str,
        end: str,
        typecode: str,
    ) -> None:
        """
        Insert partitions onto a disk.

        # Params

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
        """

        if self.devtype not in ["disk", "loop"]:
            raise BlockDeviceError("Only disks may be partitioned.")

        SGDisk.create_partition(
            devpath=self.path,
            part_number=str(part_number),
            start_sector=start,
            end_sector=end,
        )
        SGDisk.set_partition_type(
            devpath=self.path,
            part_number=str(part_number),
            typecode=typecode,
        )

        self.probe()

    def probe(self) -> None:
        """Probe for partitions."""

        if self.devtype not in ["disk", "loop"]:
            raise BlockDeviceError("Only disks may be probed for partitions.")

        PartProbe.probe_device(self.path)
        self.sync()

    def sync(self) -> None:
        """Update self with current data."""

        time.sleep(0.01)
        blockdev = Lsblk.list_one(self.path)["blockdevices"][0]
        self.update(blockdev)

    def unmount(self) -> None:
        """Unmount child devices."""

        for child in self._children:
            child.unmount()

        for mountpoint in self.get("mountpoints", []):
            if mountpoint is None:
                continue
            log.info("Unmounting %s", mountpoint)
            Umount.umount(mountpoint=mountpoint)

    def update(self, attrs: Dict[Any, Any]) -> None:
        """
        Updates device data.

        # Params
          = attrs (dict): A dictinonary of attribute names and values that
          should be added to self._data. The "path" and keys refer to
          properties block device in the kernel and needs to be added to the
          BlockDevice object's _data basically immediately. Those keys are
          also the few keys that can't change, so `avoid_overwrite` is used to
          treat those keys like an XOR. If a key is provided in self._data and
          kwargs and they aren't the same value `avoid_overwrite` raises a
          `KeyError`. If it's provided in both but they are the same value
          `avoid_overwrite` continues as normal. If it's in neither
          `avoid_overwrite` raises a `KeyError`. If it's in one or the other
          it will be either: left alone in _data or added to _data as
          relevant.
        """

        path = self.get("path")
        path = attrs["path"] if path is None else path

        log.info("Updating data for %s", path)

        incoming = attrs.pop("children", [])

        # Avoid overwrite
        for key, value in attrs.items():
            if (
                key in ["path", "back-file", "type"]
                and key in self._data
                and value != self._data[key]
            ):
                raise KeyError(
                    f"Cannot update self with '{key}': {value} != {self._data[key]}."
                )

        self._data.update(attrs)

        while incoming:
            incoming_child = incoming.pop(0)

            for child in self._children:
                if incoming_child["path"] == child.path:
                    child.update(incoming_child)
                    incoming_child = None
                    break

            if incoming_child is not None:
                blockdev = BlockDevice()
                blockdev.update(incoming_child)
                self._children.append(blockdev)


class Storage:
    """
    A storage object representing a storage device, real or image file.
    """

    # TODO: Translate filepaths in storage root to host root

    def __init__(self, storage: dict):
        """
        Storage object.

        # Params

          - storage (dict): A dictionary representing a device and it's
            partition layout.
        """

        self._cfg = storage

        self._device = BlockDevice.as_image_file(
            path=self._cfg["disk"]["path"], size=self._cfg["disk"]["size"]
        )

        self._mount_dir = tempfile.mkdtemp()

        log.info("Found device file: %s", self._device.path)

    @property
    def root(self):
        """Return the root of the mounted BlockDevice partitions."""
        return self._mount_dir

    def close(self) -> None:
        """Clean up."""

        self._device.unmount()
        self._device.close()

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
            fs_cfg = part["filesystem"]

            self._device.add_part(
                start=part["start"],
                end=part["end"],
                typecode=part["typecode"],
                fs_type=fs_cfg["type"],
                fs_args=fs_cfg.get("args"),
                fs_label=fs_cfg.get("label"),
                fs_label_flag=fs_cfg.get("label_flag", "-L"),
            )

    def mount(self) -> None:
        """
        Mount filesystems per configuration.

        Mount identifies the listed mountpoints in the provided configuration,
        compiles them into a single list, then sorts them alphabetically so
        earlier directories will be mounted before later directories. `swap`
        is treated as a special mountpoint, swap partitions won't be mounted
        but their corresponding BlockDevices will be marked as swap partitions
        so they can be added to fstab later. Multiple partitions can be marked
        as swap but otherwise if multiple partitions have the same mountpoint
        only the last partition listed in the configuration will be mounted.

        The key `host_mountpoint` will be added to each partition in storages
        internal BlockDevice to keep track of what's where.
        """

        mount_order = []  # Order the mountpoints so they're mounted ccrrectly.
        mount_mapping = {}

        for index, item in enumerate(self._cfg["layout"]):
            mountpoint = item["filesystem"]["mountpoint"]

            if mountpoint == "swap":
                # Swap isn't "mountpoint", so it needs to be handled
                # differently, also multiple partitions can be marked as swap.

                self._device.children[index].update(
                    attrs={"host_mountpoint": "swap"}
                )

            else:
                # remove the leading /
                mountpoint = os.sep.join(mountpoint.split(os.sep)[1:])

                host_mountpoint = os.path.join(self._mount_dir, mountpoint)

                mount_order.append(host_mountpoint)
                mount_mapping[host_mountpoint] = self._device.children[index]

                self._device.children[index].update(
                    attrs={"host_mountpoint": host_mountpoint}
                )

        mount_order.sort()

        for mountpoint in mount_order:
            devpath = mount_mapping[mountpoint].path

            if not os.path.exists(mountpoint):
                os.makedirs(mountpoint)

            Mount.mount(devpath=devpath, mountpoint=mountpoint)

        self._device.sync()
