"""Install Operating Systems on VM images."""

import logging
from sysbuilder.config import Config
from sysbuilder.storage import Storage

log = logging.getLogger(__name__)


def main():
    """Main."""

    cfg = Config("config.json")

    vdi = Storage(storage=cfg.get("Storage"))
    vdi.format()


if __name__ == "__main__":
    main()
