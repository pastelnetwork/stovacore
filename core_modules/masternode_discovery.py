import os
from core_modules.settings import NetWorkSettings


def discover_nodes(regtestdir):
    settings_list = []
    for dir in sorted(os.listdir(regtestdir)):
        basedir = os.path.join(regtestdir, dir)

        settings = read_settings_file(basedir)
        settings_list.append(settings)

    return settings_list


def read_settings_file(basedir):
    nodename = os.path.basename(basedir).rstrip("/").lstrip("node")
    settingsfile = os.path.join(basedir, NetWorkSettings.CDAEMON_CONFIG_FILE)

    settings = {}
    for line in open(settingsfile):
        line = line.strip().split("=")
        settings[line[0]] = line[1]

    # cast types
    settings["rpcport"] = int(settings["rpcport"])
    settings["port"] = int(settings["port"])

    # set our settings
    # TODO: cofidy these settings in a concrete model and validate that everything we need is set
    settings["cdaemon_conf"] = settingsfile
    settings["nodename"] = nodename
    settings["datadir"] = basedir                       # TODO: these names are not great
    settings["basedir"] = os.path.join(basedir, "pymn")
    settings["ip"] = "127.0.0.1"
    settings["pyrpcport"] = int(settings["rpcport"]) + 1000
    settings["pyhttpadmin"] = int(settings["rpcport"]) + 2000
    settings["pubkey"] = os.path.join(settings["basedir"], "config", "public.key")

    return settings
