"""Test shell module."""

# pylint: disable=C0103,W0212,W0201

import os
from subprocess import CalledProcessError
import tempfile
import unittest
from jsonschema import validate
from sysbuilder.config import Config
from sysbuilder.storage import Storage
from sysbuilder.shell import (
    ArchChroot,
    DD,
    Losetup,
    Lsblk,
    Mkfs,
    Mkswap,
    Mount,
    Pacstrap,
    PartProbe,
    SGDisk,
    Umount,
)
from tests.data.lsblk_validate import validate_json


class ArchChrootTest(unittest.TestCase):
    """Test instances of the arch-chroot."""

    def setUp(self):
        """Set up."""

        tmpd = tempfile.mkdtemp()
        self.img_path = f"{tmpd}/disk.img"
        self.cfg = Config(
            check=False,
            cfg={
                "storage": {
                    "disk": {
                        "path": self.img_path,
                        "type": "sparse",
                        "ptable": "gpt",
                        "size": "32G",
                    },
                    "layout": [
                        {
                            "start": "",
                            "end": "+100M",
                            "typecode": "ef00",
                            "filesystem": {
                                "type": "vfat",
                                "label": "EFI",
                                "args": ["-F", "32"],
                                "label_flag": "-n",
                                "mountpoint": "/efi",
                            },
                        },
                        {
                            "start": "",
                            "end": "+4G",
                            "typecode": "8200",
                            "filesystem": {
                                "type": "swap",
                                "label": "swap",
                                "mountpoint": "swap",
                            },
                        },
                        {
                            "start": "",
                            "end": "",
                            "typecode": "8300",
                            "filesystem": {
                                "type": "ext4",
                                "label": "root",
                                "mountpoint": "/",
                            },
                        },
                    ],
                }
            },
        )

    def tearDown(self):
        """
        Clean up.
        """

        ArchChroot.chroot(
            chroot_dir=self.vdi.root,
            chroot_command="gpgconf",
            chroot_command_args=[
                "--homedir",
                "/etc/pacman.d/gnupg",
                "--kill",
                "gpg-agent",
            ],
        )

        self.vdi._device.unmount()
        Losetup.detach(fp=self.vdi._device.path)

    def test_install(self):
        """Test pacstrap with packages."""

        self.vdi = Storage(storage=self.cfg.get("storage"))
        self.vdi.format()
        self.vdi.mount()

        for child in self.vdi._device.children:
            host_mountpoint = child.get("host_mountpoint")

            if host_mountpoint == "swap":
                continue

        Pacstrap.install(
            fs_root=self.vdi.root,
            packages=[
                "openssh",
                "iptables",
                "python3",
                "reflector",
                "base",
                "linux",
                "grub",
                "efibootmgr",
                "cloud-init",
            ],
        )

        ArchChroot.chroot(
            chroot_dir=self.vdi.root,
            chroot_command="/usr/bin/touch",
            chroot_command_args=["/IAMAMAGICFILE"],
        )

        self.assertTrue(
            os.path.exists(os.path.join(self.vdi.root, "IAMAMAGICFILE"))
        )


class DdTest(unittest.TestCase):
    """Test instances of dd command."""

    def setUp(self):
        """Test path."""
        self.file = os.path.join(tempfile.mkdtemp(), "disk.img")

    def tearDown(self):
        """Clean up"""

        os.remove(self.file)
        os.removedirs(os.path.dirname(self.file))

    def test_dd_sparse(self):
        """Test sparse file creation."""

        DD.write_file(
            input_file="/dev/zero",
            output_file=self.file,
            count="2048",
            convs=["sparse"],
        )

        blocks_utilized = os.stat(self.file).st_blocks

        self.assertEqual(blocks_utilized * 512, 0)

    def test_dd(self):
        """Test file creation."""

        DD.write_file(
            input_file="/dev/zero", output_file=self.file, count="2048"
        )

        blocks_utilized = os.stat(self.file).st_blocks

        self.assertEqual(blocks_utilized * 512, 2147483648)


class FormatDiskTest(unittest.TestCase):
    """Test runs of partprobe."""

    def setUp(self):
        """Test file."""

        self.file = os.path.join(tempfile.mkdtemp(), "disk.img")
        DD.write_file(
            input_file="/dev/zero",
            output_file=self.file,
            count="2048",
            convs=["sparse"],
        )
        Losetup.attach(self.file)
        self.dev = Losetup.identify(self.file)

    def tearDown(self):
        """Clean up"""

        Losetup.detach(self.dev)
        os.remove(self.file)
        os.removedirs(os.path.dirname(self.file))

    def test_sgdisk(self):
        """Test sgdisk"""

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]
        self.assertIsNone(loop.get("children"))

        SGDisk.create_partition(
            devpath=self.dev,
            part_number="1",
            start_sector="",
            end_sector="+512M",
        )
        SGDisk.create_partition(
            devpath=self.dev,
            part_number="2",
            start_sector="",
            end_sector="+512M",
        )
        SGDisk.create_partition(
            devpath=self.dev,
            part_number="3",
            start_sector="",
            end_sector="",
        )

        SGDisk.set_partition_type(
            devpath=self.dev, part_number="1", typecode="ef00"
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="2", typecode="8200"
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="3", typecode="8300"
        )

        PartProbe.probe_device(self.dev)

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]
        self.assertEqual(len(loop.get("children", [])), 3)

    def test_fs_creation(self):
        """Test mkfs"""

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]
        self.assertIsNone(loop.get("children"))

        SGDisk.create_partition(
            devpath=self.dev,
            part_number="1",
            start_sector="",
            end_sector="+512M",
        )
        SGDisk.create_partition(
            devpath=self.dev,
            part_number="2",
            start_sector="",
            end_sector="+512M",
        )
        SGDisk.create_partition(
            devpath=self.dev,
            part_number="3",
            start_sector="",
            end_sector="",
        )

        SGDisk.set_partition_type(
            devpath=self.dev, part_number="1", typecode="ef00"
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="2", typecode="8200"
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="3", typecode="8300"
        )

        PartProbe.probe_device(self.dev)

        loop = Lsblk.list_one(self.dev)["blockdevices"][0]

        loopc1 = loop["children"][0]
        loopc2 = loop["children"][1]
        loopc3 = loop["children"][2]

        self.assertIsNone(loopc1["fstype"])
        self.assertIsNone(loopc2["fstype"])
        self.assertIsNone(loopc3["fstype"])

        Mkfs.create(devpath=loopc1["path"], fstype="vfat", fs_args=["-F", "32"])
        loopc1 = Lsblk.list_one(self.dev)["blockdevices"][0]["children"][0]
        loopc1a = Lsblk.list_one(f"{self.dev}p1")["blockdevices"][0]

        Mkswap.create(devpath=loopc2["path"])
        loopc2 = Lsblk.list_one(self.dev)["blockdevices"][0]["children"][1]
        loopc2a = Lsblk.list_one(f"{self.dev}p2")["blockdevices"][0]

        Mkfs.create(devpath=loopc3["path"], fstype="ext4")
        loopc3 = Lsblk.list_one(self.dev)["blockdevices"][0]["children"][2]
        loopc3a = Lsblk.list_one(f"{self.dev}p3")["blockdevices"][0]

        # loop = Lsblk.list_one(self.dev)["blockdevices"][0]

        self.assertEqual(loopc1["fstype"], "vfat")
        self.assertEqual(loopc2["fstype"], "swap")
        self.assertEqual(loopc3["fstype"], "ext4")

        self.assertEqual(loopc1, loopc1a)
        self.assertEqual(loopc2, loopc2a)
        self.assertEqual(loopc3, loopc3a)


class LosetupTest(unittest.TestCase):
    """Test instances of losetup command."""

    def setUp(self):
        """Test file."""

        self.file = os.path.join(tempfile.mkdtemp(), "disk.img")
        DD.write_file(
            input_file="/dev/zero",
            output_file=self.file,
            count="2048",
            convs=["sparse"],
        )
        if not os.path.exists(self.file):
            raise FileNotFoundError(self.file)

    def tearDown(self):
        """Clean up"""

        os.remove(self.file)
        os.removedirs(os.path.dirname(self.file))

    def test_losetup(self):
        """Test losetup attach and detach"""

        Losetup.attach(self.file)

        dev = Losetup.identify(self.file)
        Lsblk.list_one(dev)

        Losetup.detach(dev)
        with self.assertRaises(CalledProcessError):
            Lsblk.list_one(dev)  # The files still exist but lsblk fails.

    def test_losetup_identify(self):
        """Test losetup identify"""

        Losetup.attach(self.file)

        dev = Losetup.identify(self.file)
        Lsblk.list_one(dev)

        dev2 = Losetup.identify(self.file)

        self.assertEqual(dev, dev2)

        Losetup.detach(dev)
        with self.assertRaises(CalledProcessError):
            Lsblk.list_one(dev)  # The files still exist but lsblk fails.


class LsblkTest(unittest.TestCase):
    """Test instances of lsblk command."""

    @staticmethod
    def _lsblk_recurse(testlist: list):
        validate(testlist, validate_json)
        for result in testlist:
            children = result.get("children")
            if children is not None:
                LsblkTest._lsblk_recurse(children)

    def test_lsblk_all(self):
        """lsblk with no arguments"""

        results = Lsblk.list_all()["blockdevices"]
        self._lsblk_recurse(results)

    def test_lsblk_sda(self):
        """lsblk with one device argument"""

        # Generally people have sata or nvme, sometimes even both
        for disk_name in ["/dev/sda", "/dev/nvme0n1", "/dev/vda"]:
            try:
                results = Lsblk.list_one(disk_name)["blockdevices"]
                self._lsblk_recurse(results)
            except FileNotFoundError:
                results = None
                continue

    def test_lsblk_fail(self):
        """lsblk with one nondevice argument"""

        with self.assertRaises(ValueError):
            Lsblk.list_one("/bin/ls")


class MountTest(unittest.TestCase):
    """Test the mount/unmount class."""

    def setUp(self):
        """Setup a loop device."""

        self.mountpoint = tempfile.mkdtemp()

        self.file = os.path.join(tempfile.mkdtemp(), "disk.img")
        DD.write_file(
            input_file="/dev/zero",
            output_file=self.file,
            count="2048",
            convs=["sparse"],
        )
        Losetup.attach(self.file)
        self.dev = Losetup.identify(self.file)

        SGDisk.create_partition(
            devpath=self.dev,
            part_number="1",
            start_sector="",
            end_sector="",
        )
        SGDisk.set_partition_type(
            devpath=self.dev, part_number="1", typecode="8300"
        )

        PartProbe.probe_device(self.dev)

        self.loop = Lsblk.list_one(self.dev)["blockdevices"][0]

        Mkfs.create(
            devpath=self.loop["children"][0]["path"],
            fstype="ext4",
        )

    def tearDown(self):
        """Remove a loop device and cleanup it's backing file."""

        Losetup.detach(self.dev)
        os.remove(self.file)
        os.removedirs(os.path.dirname(self.file))
        os.removedirs(self.mountpoint)

    def test_mount_and_unmount(self):
        """Test mounting and unmounting a partition."""

        Mount.mount(
            devpath=self.loop["children"][0]["path"], mountpoint=self.mountpoint
        )
        self.assertTrue(os.path.ismount(self.mountpoint))

        Umount.umount(mountpoint=self.mountpoint)
        self.assertFalse(os.path.ismount(self.mountpoint))


class PacstrapTest(unittest.TestCase):
    """Test Pacstrap command."""

    def setUp(self):
        """Set up."""

        self.fake_root = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""

        # This is required to kill the running gpg-agent proces in the chroot
        # so it can be unmounted/removed/cleaned up
        ArchChroot.chroot(
            chroot_dir=self.fake_root,
            chroot_command="gpgconf",
            chroot_command_args=[
                "--homedir",
                "/etc/pacman.d/gnupg",
                "--kill",
                "gpg-agent",
            ],
        )

    def test_install(self):
        """Test pacstrap with packages."""

        Pacstrap.install(
            fs_root=self.fake_root,
            packages=[
                "openssh",
                "iptables",
                "python3",
                "reflector",
                "base",
                "linux",
                "grub",
                "efibootmgr",
                "cloud-init",
            ],
        )

        test_paths = {
            "sshd_cfg": "etc/ssh/sshd_config",
            "reflector_cfg": "etc/xdg/reflector/reflector.conf",
            "grub_cfg": "etc/default/grub",
            "cloud_init_cfg": "etc/cloud/cloud.cfg",
            "iptables_sample_rules": "usr/share/iptables/simple_firewall.rules",
            "python3_exe": "usr/bin/python3",
            "efibootmgr_exe": "usr/bin/efibootmgr",
            "linux_img": "boot/vmlinuz-linux",
        }

        for k, v in test_paths.items():
            try:
                self.assertTrue(os.path.exists(os.path.join(self.fake_root, v)))
            except AssertionError as assert_err:
                raise AssertionError(k) from assert_err
