### Fetching submodules

This repository uses git submodules feature. To fetch modules run:
 - `git submodule init && git submodule update`

### Install and run pyNode (Ubuntu 18.04)

 - `pasteld` should be started and running
 - python3.6 should be installed
 - `apt install python3-pip`
 - `pip3 install -r requirements.txt`
 - `python start_single_masternode.py &`
 - pyNode is running, listening connections on port 444

### Tools/scripts

 - `update_pynodes.sh` - prepare pyNode distirbution package from content of the current directory. Updates all masternode of testnet (masternodes should be added to local ssh config with names [ mn2, ..., mn11 ]
 - `pynode_control.sh` - helping script, should not be executed directly. It is executed on masternode machine by `pynodes.sh` script
 - `pynodes.sh` - provides start/stop/status functionality for pynodes of the testnet. Connects to testnet machines and executes `pynode_control.sh` fetched from 3rd party host. Return result to the local console. `Parameters`: `start` | `stop` | `status`. Applied to all known masternodes of testnet (mn2 .. mn11)
 - `python test_rpc.py` - connects to pyNodes from local `masternodes.conf` file, send ping packet with zeroMQ RPC. If any node hangs with response - it probably requires restart.
