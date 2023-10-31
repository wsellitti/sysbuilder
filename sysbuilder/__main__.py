"""Install Operating Systems on VM images."""

import logging
from sysbuilder.config import Config
from sysbuilder.storage import Storage

log = logging.getLogger(__name__)


def main():
    """Main."""

    cfg = Config.from_file("config.json")

    vdi = Storage(storage=cfg.get("storage"))
    vdi.format()


if __name__ == "__main__":
    main()
