"""Install Operating Systems on VM images."""

import logging
from sysbuilder._helper import read_config
from sysbuilder.storage import Storage

log = logging.getLogger(__name__)


def main():
    """Main."""

    cfg = read_config("config.json")

    vdi = Storage(storage=cfg["storage"])
    vdi.format()


if __name__ == "__main__":
    main()
