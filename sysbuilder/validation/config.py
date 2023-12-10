"""Validate sysbuilder configuration."""

from typing import Dict
from jsonschema import validate
from sysbuilder.validation.helpers import type_dict, type_list, type_str


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
            "package_manager": type_str(enum=["pacman"]),
            "packages": type_list(items=type_str()),
            "services": type_dict(
                properties={
                    "enabled": type_list(items=type_str()),
                    "disabled": type_list(items=type_str()),
                }
            ),
            "files": type_list(
                items=type_dict(
                    properties={
                        "src": type_str(),
                        "dest": type_str(),
                        "mode": type_str(pattern=r"[0-2]?\d{3}"),
                        "owner": type_str(),
                        "group": type_str(),
                    },
                    required=["src", "dest", "mode", "owner", "group"],
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
