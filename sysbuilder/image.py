"""
This module concerns the VDIs that will be created by sysbuilder. 
"""

import logging
import os
from shutil import chown, copy, copytree
from subprocess import CalledProcessError
from typing import Any, Dict
from sysbuilder.config import Config
from sysbuilder.shell import ArchChroot, Pacstrap
from sysbuilder.storage import Storage

log = logging.getLogger(__name__)


class VDI:
    """Virtual Disk Image class."""

    def __init__(
        self, cfg: Dict[Any, Any] | None = None, cfg_path: str | None = None
    ):
        """
        Init.

        # Params

          - cfg (dict): The configuration for storage and what should go on
            it.
          - cfg_path (str): A path to the JSON file containing configuration data.
        """

        if cfg is not None:
            self._cfg = Config(cfg)
        elif cfg_path is not None:
            self._cfg = Config.from_file(cfg_path)
        else:
            raise ValueError("Configs or a config file must be provided.")

        self._install_cfg = self._cfg.get("install")
        self._storage_cfg = self._cfg.get("storage")

        self._storage = Storage(self._storage_cfg)

    @staticmethod
    def _copy_file(
        root: str, src: str, dest: str, mode: str, owner: str, group: str
    ):
        """Copy files to vdi"""

        if os.path.abspath(dest):
            dest = os.path.relpath(dest, "/")
        dest = os.path.join(root, dest)

        copy(src=src, dst=dest)

        os.chmod(dest, mode=int(mode, base=8))

        vdi_owner_id = int(
            ArchChroot.chroot(
                chroot_dir=root,
                chroot_command="getent",
                chroot_command_args=["passwd", owner],
            ).split(":")[2]
        )

        vdi_group_id = int(
            ArchChroot.chroot(
                chroot_dir=root,
                chroot_command="getent",
                chroot_command_args=["group", group],
            ).split(":")[2]
        )

        chown(path=dest, user=vdi_owner_id, group=vdi_group_id)

    @staticmethod
    def _copy_directory(
        root: str, src: str, dest: str, mode: str, owner: str, group: str
    ):
        """Copy directories to vdi"""

        if os.path.abspath(dest):
            dest = os.path.relpath(dest, "/")
        dest = os.path.join(root, dest)

        copytree(src=src, dst=dest)

        os.chmod(dest, mode=int(mode, base=8))

        vdi_owner_id = int(
            ArchChroot.chroot(
                chroot_dir=root,
                chroot_command="getent",
                chroot_command_args=["passwd", owner],
            ).split(":")[2]
        )

        vdi_group_id = int(
            ArchChroot.chroot(
                chroot_dir=root,
                chroot_command="getent",
                chroot_command_args=["group", group],
            ).split(":")[2]
        )

        chown(path=dest, user=vdi_owner_id, group=vdi_group_id)

    @staticmethod
    def _create_symlink(root: str, src: str, dest: str):
        """Create symlinks in the vdi."""

        if os.path.abspath(dest):
            host_dest = os.path.relpath(dest, "/")
        host_dest = os.path.join(root, host_dest)

        os.makedirs(os.path.dirname(host_dest))

        ArchChroot.chroot(
            chroot_dir=root,
            chroot_command="ln",
            chroot_command_args=["-s", src, dest],
        )

    def _archlinux_system(self):
        """Install an arch based system."""

        packages = self._install_cfg.get("packages", [])
        packages.append("base")

        # Archlinux install only supports Pacstrap
        Pacstrap.install(fs_root=self._storage.root, packages=packages)

        # Disable root
        if self._install_cfg.get("disable_root", True):
            ArchChroot.chroot(
                self._storage.root,
                chroot_command="usermod",
                chroot_command_args=["--lock", "--expiredate", "1", "root"],
            )

    def _files(self):
        """Add files to vdi"""

        files = self._install_cfg.get("files", [])
        for f in files:
            src = f["src"]
            dest = f["dest"]
            ftype = f["type"]
            mode = f.get("mode")
            owner = f.get("owner")
            group = f.get("group")

            if ftype != "link":
                if mode is None:
                    raise ValueError(
                        f"'mode' must be a provided key if type is not link!: {f}",
                    )
                if owner is None:
                    raise ValueError(
                        f"'owner' must be a provided key if type is not link!: {f}",
                    )
                if group is None:
                    raise ValueError(
                        f"'owner' must be a provided key if type is not link!: {f}",
                    )

            if ftype == "link":
                self._create_symlink(self._storage.root, src=src, dest=dest)
            if ftype == "directory":
                self._copy_directory(
                    self._storage.root,
                    src=src,
                    dest=dest,
                    mode=mode,
                    owner=owner,
                    group=group,
                )
            if ftype == "file":
                self._copy_file(
                    self._storage.root,
                    src=src,
                    dest=dest,
                    mode=mode,
                    owner=owner,
                    group=group,
                )

    def _grub(self):
        """Install grub"""

        # TODO: pull target from config
        # TODO: pull efi directory from config
        ArchChroot.chroot(
            chroot_dir=self._storage.root,
            chroot_command="grub-install",
            chroot_command_args=[
                "--target=x86_64-efi",
                "--boot-directory=/boot",
                "--efi-directory=/efi",
                self._storage._device.path,  # pylint: disable=W0212
            ],
        )

        ArchChroot.chroot(
            chroot_dir=self._storage.root,
            chroot_command="grub-mkconfig",
            chroot_command_args=["-o", "/boot/grub/grub.cfg"],
        )

        # Install grub in a default place.
        # TODO: pull efi directory from config
        efi_arch = os.path.join(
            self._storage.root, "efi", "EFI", "arch", "grubx64.efi"
        )
        efi_generic_dir = os.path.join(self._storage.root, "efi", "EFI", "BOOT")
        efi_generic = os.path.join(efi_generic_dir, "BOOTX64.efi")

        os.makedirs(efi_generic_dir)
        copy(efi_arch, efi_generic)

    def _initramfs(self):
        """
        Recreate initramfs. Run at the end of create automatically incase
        anything has happened that would justify recreating the initram.
        """

        installed_kernel = os.listdir(
            os.path.join(self._storage.root, "usr", "lib", "modules")
        )[0]

        ArchChroot.chroot(
            chroot_dir=self._storage.root,
            chroot_command="mkinitcpio",
            chroot_command_args=[
                "-k",
                installed_kernel,
                "-g",
                "/boot/initramfs-linux.img",
            ],
        )

    def _locale(self):
        """Set locale information."""

        locale = self._install_cfg.get("locale", ["en_US.UTF-8 UTF-8"])
        if isinstance(locale, str):
            locale = [locale]

        # TODO: Fix encoding
        with open(
            file=os.path.join(self._storage.root, "etc/locale.conf"),
            mode="a",
            encoding="UTF-8",
        ) as f:
            for l in locale:
                f.write(f"{l}\n")

        ArchChroot.chroot(self._storage.root, chroot_command="locale-gen")

    def _systemd(self):
        """
        Enable/disable services in a systemd-based system.
        """

        enabled_services = self._install_cfg.get("services").get("enabled")
        disabled_services = self._install_cfg.get("services").get("disabled")

        if enabled_services is not None:
            args = ["enable"]
            args.extend(enabled_services)
            ArchChroot.chroot(
                self._storage.root,
                chroot_command="systemctl",
                chroot_command_args=args,
            )

        if disabled_services is not None:
            args = ["disable"]
            args.extend(disabled_services)
            ArchChroot.chroot(
                self._storage.root,
                chroot_command="systemctl",
                chroot_command_args=args,
            )

    def _timezone(self):
        """Set the timezone."""

        timezone = self._install_cfg.get("timezone", "UTC")
        timezone_file = f"/usr/share/zoneinfo/{timezone}"

        ArchChroot.chroot(
            self._storage.root,
            chroot_command="ln",
            chroot_command_args=["-s", timezone_file, "/etc/localtime"],
        )

    def _users(self):
        """
        Configure user accounts.

        If no users are provided in the ocnfiguration a default user account
        with credentials user/password will be created instead.

        Creating a user account with a password of None will disable the
        password for that user account.
        """

        default_user = {
            "name": "user",
            "gecos": "Default User",
            "password": "$6$jW4LnOFrEdUujayf$vpC4OSBi3Uo8yuGpLDjgB4CHMk8rnqzk3rDt6tFzHJcJlM2OKKnGbA6QZllJGr9ur/2SxdxdALgFzEiEvYYeW/",
            "user_id": 1000,
        }

        users = self._install_cfg.get("users", [default_user])

        for user in users:
            name = user["name"]
            gecos = user.get("gecos", name)
            password = user.get("password")
            group = user.get("group", name)
            service_account = user.get("service_account", False)
            additional_groups = user.get("additional_groups")
            home_dir = user.get("home_dir")
            shell = user.get("shell", "/bin/bash")
            create_home = user.get("create_home", True)
            ssh_keys = user.get("ssh_keys", [])

            useradd_args = ["-g", group, "-c", gecos, "-s", shell]

            if home_dir is not None:
                useradd_args.extend(["-d", home_dir])
            if additional_groups is not None:
                useradd_args.extend(["-G", ",".join(additional_groups)])
            if service_account:
                useradd_args.extend(["-r"])
            if password is not None:
                useradd_args.extend(["-p", password])
            if create_home:
                useradd_args.extend(["-m"])

            useradd_args.append(name)

            try:
                # TODO: Make getent command.
                ArchChroot.chroot(
                    chroot_dir=self._storage.root,
                    chroot_command="getent",
                    chroot_command_args=["group", group],
                )
            except CalledProcessError as cpe:
                if cpe.returncode == 2:
                    ArchChroot.chroot(
                        chroot_dir=self._storage.root,
                        chroot_command="groupadd",
                        chroot_command_args=[group],
                    )
                else:
                    raise cpe

            ArchChroot.chroot(
                chroot_dir=self._storage.root,
                chroot_command="useradd",
                chroot_command_args=useradd_args,
            )

            if ssh_keys:
                home_dir = ArchChroot.chroot(
                    chroot_dir=self._storage.root,
                    chroot_command="getent",
                    chroot_command_args=["passwd", name],
                ).split(":")[5]

                if os.path.abspath(home_dir):
                    home_dir = os.path.relpath(home_dir, "/")
                home_dir = os.path.join(self._storage.root, home_dir)

                os.makedirs(name=os.path.join(home_dir, ".ssh"))

                ssh_keyfile = os.path.join(home_dir, ".ssh", "authorized_keys")

                # TODO: Fix encoding
                with open(
                    file=os.path.join(home_dir, ".ssh", "authorized_keys"),
                    mode="w",
                    encoding="utf-8",
                ) as f:
                    for key in ssh_keys:
                        f.write(f"{key}\n")

                vdi_owner_id = int(
                    ArchChroot.chroot(
                        chroot_dir=self._storage.root,
                        chroot_command="getent",
                        chroot_command_args=["passwd", name],
                    ).split(":")[2]
                )

                vdi_group_id = int(
                    ArchChroot.chroot(
                        chroot_dir=self._storage.root,
                        chroot_command="getent",
                        chroot_command_args=["group", group],
                    ).split(":")[2]
                )

                chown(path=ssh_keyfile, user=vdi_owner_id, group=vdi_group_id)

                os.chmod(path=ssh_keyfile, mode=0o600)

    def close(self):
        """Clean up scratch directories."""

        self._storage.close()

    def create(self):
        """Create the VDI."""

        self._storage.format()
        self._storage.mount()

        if self._install_cfg["base"] == "archlinux":
            self._archlinux_system()
        else:
            raise ValueError(
                "The base install system must be one of the following: ['archlinux']."
            )

        if self._install_cfg["service_manager"] == "systemd":
            self._systemd()
        else:
            raise ValueError(
                "The process management system must be one of the following: ['systemd']."
            )

        self._locale()
        self._timezone()
        self._users()
        self._files()
        self._initramfs()
        self._grub()
