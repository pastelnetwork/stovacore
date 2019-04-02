import os
import sys

from masternode_prototype.masternode_daemon import MasterNodeDaemon
from core_modules.masternode_discovery import read_settings_file

if __name__ == "__main__":
    basedir = sys.argv[1]
    bindip = sys.argv[2]
    nodes = None
    if len(sys.argv) > 3:
        nodes = [sys.argv[3]]

    cdaemon_conf = os.path.join(basedir, "pastel.conf")
    settings = read_settings_file(basedir)
    settings["ip"] = bindip

    mnd = MasterNodeDaemon(settings=settings, addnodes=nodes)
    mnd.run_event_loop()
masternode_logic.py