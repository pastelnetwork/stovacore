from masternode_prototype.masternode_daemon import MasterNodeDaemon

# TODO: as this code runs a single instance of masternode - some entities definetely
# TODO: should be global and instantiated only one.
# TODO: this entities are:
# TODO: - blockchain connection
# TODO: - pastelid
# TODO: - passphrase for pastelID
# TODO: - basedir
# TODO: (to be continued)

# TODO: Currently all this entites are instantiated in MasterNodeDaemon class, and are passed through the
# TODO: whole class hierarchy down to the bottom level. It should be fixed.

if __name__ == "__main__":
    mnd = MasterNodeDaemon()
    mnd.run_event_loop()
