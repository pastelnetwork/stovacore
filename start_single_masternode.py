from masternode_prototype.masternode_daemon import MasterNodeDaemon


if __name__ == "__main__":
    mnd = MasterNodeDaemon()
    mnd.run_event_loop()
