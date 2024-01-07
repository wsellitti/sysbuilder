"""Install Operating Systems on VM images."""

import logging
from sysbuilder.image import VDI

log = logging.getLogger(__name__)


def main():
    """Main."""

    vdi = VDI(cfg_path="config.json")
    vdi.create()


if __name__ == "__main__":
    main()
