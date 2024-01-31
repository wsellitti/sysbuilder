"""
Validate sysbuilder configuration.

# Configuration (dict)

The configuration must contain at least the following top level keys:
  - storage (dict): Governs the storage type, partition scheme, and installed
    filesystems.
  - install (dict): Gooverns installed packages, enabled services, additional
    files, and the package manager.

## Storage (dict)

The storage configuration must contain at least the following top level keys:
['disk', 'layout'].

### Disk

Describes the storage "device". `disk` must contain at least the following
keys: ['path', 'type', 'ptable'], but may also contain the keys ['size'].

  - path (str): This can be a path to either a device file (in /dev or /sys)
    or to a disk image file. `type` must be the appropriate corresponding
    value. If `type` is 'physical' the file provided in `path` must exist
    before this script is run.
  - type (str): This can be one of 3 values:
      - physical: The value in `path` must point to a physical block
      device. - sparse: The value in `path` will be assumed to be a virtual
      device. 'sparse' virtual devices will be created as a sparse files and
      will only allocate data as they're used. - raw: Similar to sparse, but
      raw devices will allocate all their intended storage at one time.
  - ptable (str): The partition table type, only supports 'gpt' at this time.
    A `ptable` value of 'gpt' will case sysbuilder to use `sgdisk` to
    partition the disk.
  - size (str): This should be a string shortened according to standard
    notation: '32G', '234M', '1T'. These values are in powers of 1024 not
    1000.

### Layout (list)

Describes the partition layout on the storage device, as well as filesystems
on those partitions. Each item in `layout` must contain at least the following
keys: ['start', 'end', 'typecode', 'filesystem'].

  - start (str): Sector where the partition should start. Values can be
    absolute or positions measured in standard notation: "K", "M", "G", "T".
    Providing and empty string "" will use the next available starting sector.
    Values beginning with a "+" will start the parittion that distance past
    the next available starting sector (ie, "+2G" will cause the next
    partition to start 2 gibibytes after the last partition ended). Values
    beginning with a "-"  will start the partition that distance from the next
    available ending sector with enough space (ie, "-2G" will create a
    partition that starts 2 gibibytes before the ending most available
    sector).
  - end (str): Sector where the partition should end. Values can be absolute
    or positions measured in standard notation: "K", "M", "G", "T". Providing
    and empty string "" will use the next available ending sector from the
    starting sector. Values beginning with a "+" will end the partition that
    distance past the starting sector (ie, "+2G" will create a 2 gibibyte
    partition). Values beginning with a "-" will end the partition that
    distance from the next available ending sector (ie, "-2G" will create a
    partition that 2 gibibytes short of the maximum space available for that
    partiton).
  - typecode (str): A 4-digit hexadecimal value representing partition type
    codes, as returned from `sgdisk -L`.
  - filesystem (dict): Describes the filesystem that will be installed to the
    associated partition. `filesystem` must contain at least the following
    keys ['type', 'mountpoint'], but may also contain the keys ['label',
    'args', 'label_flag', 'reformat'].
      - type (str): The filesystem type, as per `mkfs`. If the `type` is
        "swap" the command `mkswap` will be used instead of `mkfs -t`. -
        mountpoint (str): Where the filesystem will be mounted relative to the
        installed system (ie, the `mountpoint` for a filesystem that will be
        mounted on "/home" should be "/home"). If the `mountpoint` is "swap"
        the filesystem will be treated as swap space. - label (str): The
        filesystem label. No default. - label_flag (str): Some filesystems use
        nonstandard flags to create a filesystem, this is required if a label
        is provided for such an atypical filesystem partition. Defaults to
        "-L".
      - args (list): Additional arguments to be during the creation of the
        filesystem.

## Install

Describes how the OS should be installed to the newly created filesystem(s).
The required keys are ['base', and 'package_manager']

  - base (str): The base system to install. Can be one of the following:
    ['archlinux'].
  - disable_root (bool): If true (the default) the root account will be
    disabled in the new system.
  - locale (str): The system locale. This will be written to `/etc/locale.gen`
    and used to generate locales for the system.
  - package_manager (str): The package manager used to install additional
    packages. Can be one of the following: ['pacman'].
  - packages (list): A list of package names to install.
  - service_manager (str): The system service manager. Can be one of the
    following: ['systemd'].
  - services (dict): May contain 2 keys: ['enabled', 'disabled']. Each key
    points to a list of service names. The `enabled` key will make sure those
    services are 'enabled' and the `disabled` key will make sure those
    services are 'disabled'.
  - files (list): A list of dictionaries, each one representing a file object.
    File objects will usually be copied from the host to the new system. File
    items must contain the following keys: ['src', 'dest', 'type'] and may
    contain the additional keys: ['owner', 'group', 'mode'].
      - src (str): The source filepath. This should be relative to the host,
        unless the type is "link", then this should be relative to the newly
        installed system.
      - dest (str): The destination filepath. This should relative to the
        newly installed system.
      - type (str): The type of file. This dictates the final action that will
        be performed, for 'file' or 'directory' the src will be copied to the
        destination. For 'link' a symlink will be created in the system at
        `dest` that points to `src`. `type` can be one of the following:
        ['file', 'directory', 'link'].
      - owner (str): The user who will own the new file. This will be ignored
        if `type` is 'link'.
      - group (str): The group who will own the new file. This will be ignored
        if `type` is 'link'.
      - mode (str): The mode of the new file. This will be ignored if `type`
        is 'link'.
  - timezone (str): The timezone of the new system. This should be the
    (relative) path of a file in `/usr/share/zoneinfo`.
  - users (list): A list of dictionaries, each one representing a user object.
    Users will be created on the new system, any groups listed will be created
    as well. User items must contain the following fields: ['name'] and may
    contain the following additional fields: ['gecos', 'password', 'group',
    'user_id', 'service_account', 'additional_groups', 'home_dir', 'shell',
    'create_home', 'ssh_keys'].
      - name (str): The username
      - gecos (str): The user comment (or display name).
      - password (str): The (encrypted) user password. This can be created
        with `openssl passwd`.
      - group (str): The primary group for that user.
      - user_id (int): The user's id.
      - service_account (bool): If true the account will be marked as a
        service account. Defaults to false.
      - additional_groups (list): Each item is a group to add the user too, if
        it does not exist it will be created.
      - home_dir (str): The path to the users home directory.
      - shell (str): The path to the users shell. Defaults to '/bin/bash'.
      - create_home (bool): If true the users home directory will be created
        if it does not already exist. Defaults to true.
      - ssh_keys (list): A list of ssh_keys to add to the users
        `authorized_keys` file.
  - late_commands (list): A list of simple shell commands, no support for
    advanced shell features like redirection. These run at the very end.

"""

from typing import Dict
from jsonschema import validate
from sysbuilder._validation.helpers import (
    type_bool,
    type_dict,
    type_int,
    type_list,
    type_str,
)


def check(cfg: Dict) -> None:
    """Check sysbuilder configuration data."""

    disk_schema = type_dict(
        properties={
            "ptable": type_str(enum=["gpt"]),
            "path": type_str(),
            "type": type_str(enum=["physical", "sparse", "raw"]),
            "size": type_str(pattern=r"[0-9]+[MGTP]"),
        },
        required=[
            "path",
            "ptable",
            "type",
        ],
    )

    install_schema = type_dict(
        properties={
            "base": type_str(enum=["archlinux"]),
            "disable_root": type_bool(),
            "late_commands": type_list(items=type_str()),
            "locale": type_str(),
            "package_manager": type_str(enum=["pacman"]),
            "packages": type_list(items=type_str()),
            "services": type_dict(
                properties={
                    "enabled": type_list(items=type_str()),
                    "disabled": type_list(items=type_str()),
                }
            ),
            "service_manager": type_str(enum=["systemd"]),
            "files": type_list(
                items=type_dict(
                    properties={
                        "src": type_str(),
                        "dest": type_str(),
                        "type": type_str(enum=["file", "directory", "link"]),
                        "mode": type_str(pattern=r"[0-2]?\d{3}"),
                        "owner": type_str(),
                        "group": type_str(),
                    },
                    required=["src", "dest", "type"],
                )
            ),
            "timezone": type_str(),
            "users": type_list(
                items=type_dict(
                    properties={
                        "name": type_str(),
                        "gecos": type_str(),
                        "password": type_str(or_empty=True),
                        "user_id": type_int(),
                        "service_account": type_bool(),
                        "additional_groups": type_list(items=type_str()),
                        "shell": type_str(),
                        "home_dir": type_str(),
                        "create_home": type_bool(),
                        "ssh_keys": type_list(items=type_str()),
                    },
                    required=["name"],
                )
            ),
        },
        required=["base", "package_manager"],
    )

    layout_schema = type_list(
        items=type_dict(
            properties={
                "start": type_str(),
                "end": type_str(),
                "typecode": type_str(),
                "filesystem": type_dict(
                    properties={
                        "type": type_str(),
                        "mountpoint": type_str(pattern=r"^(/.*|swap)"),
                        "label": type_str(),
                        "label_flag": type_str(),
                        "args": type_list(items=type_str()),
                    },
                    required=["type", "mountpoint"],
                ),
            },
            required=["start", "end", "typecode", "filesystem"],
        ),
        minimum_item_count=1,
        maximum_item_count=128,
    )

    schema = type_dict(
        properties={
            "storage": type_dict(
                properties={"disk": disk_schema, "layout": layout_schema},
                required=["disk", "layout"],
            ),
            "install": install_schema,
        },
        required=["storage", "install"],
    )

    validate(cfg, schema=schema)
