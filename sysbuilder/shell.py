"""Shell commands."""

import json
import logging
import os
import stat
import subprocess
import time
from typing import Any, Dict, List

log = logging.getLogger(__name__)


def dd(
    output_file: str,
    count: int,
    bs: str = "1M",
    convs: List[str] | None = None,
    input_file: str = "/dev/zero",
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

    log.debug(command)

    subprocess.run(command, capture_output=True, check=True, encoding="utf-8")


def lsblk(*args) -> Dict[Any, Any]:
    """
    lsblk wrapper

    args: Active block device files.
    """

    log.debug("Wait for a thousandth of a second before running lsblk.")
    time.sleep(0.001)

    for dev in args:
        if stat.S_ISBLK(os.stat(dev).st_mode) == 0:
            raise ValueError(f"{dev} is not a device file.")

    command = ["lsblk", "--output-all", "--json"]
    command.extend(args)

    log.debug(command)

    result = subprocess.run(
        command,
        capture_output=True,
        check=True,
        encoding="utf-8",
    )

    return json.loads(result.stdout)["blockdevices"]


def partprobe(*args):
    """partprobe wrapper"""

    for dev in args:
        if stat.S_ISBLK(os.stat(dev).st_mode) == 0:
            raise ValueError(f"{dev} is not a device file.")

    command = ["sudo", "partprobe"]
    command.extend(args)

    subprocess.run(command, check=True, capture_output=True)


def sgdisk(devpath: str, layout: Dict[str, Any]) -> None:
    """
    sgdisk wrapper

    Params
    ======
      - devpath (str):
      - layout (list): How the partitions should be laid out on the
        disk provided by `devpath`. Each item represents a different partition.

    Layout
    ------
    Each object provided by `layout` must contain at least one of the
    following sets of keys (the name of the set is not a value that needs to
    be provided, the type will be determined based on the keys in the
    dictionary).

    Partition:
      - part_number (str): The partition number.
      - start_sector (str): The on-disk sector a partition should start at.
        This can be an absolute sector number or a relative value measured in
        kibibytes, mebibytes, gibibytes, tebibytes, or prebibytes.
      - end_sector (str): The on-disk sector a partition should end at. This
        can be an absolute sector number or a relative value measured in
        kibibytes, mebibytes, gibibytes, tebibytes, or prebibytes.

    Typecode:
      - part_number (int): The partition number.
      - typecode (str): A 4-character hexadecimal value representing
        filesystem type codes.
    """

    if stat.S_ISBLK(os.stat(devpath).st_mode) == 0:
        raise ValueError(f"{devpath} is not a device file.")

    command = ["sgdisk"]

    for flag_dict in layout:
        part_num = flag_dict["part_num"]
        start_sector = flag_dict.get("start_sector")
        end_sector = flag_dict.get("end_sector")
        typecode = flag_dict.get("typecode")
        if start_sector is not None and end_sector is not None:
            addon = [
                "--new",
                ":".join([part_num, str(start_sector), str(end_sector)]),
            ]
        elif typecode is not None:
            addon = [
                "--typecode",
                ":".join([part_num, typecode]),
            ]
        else:
            raise KeyError(
                "Either start_sector and end_sector or typecode must be provided!"
            )
        command.extend(addon)
        command.append(devpath)

    subprocess.run(command, check=True, capture_output=True, encoding="utf-8")
