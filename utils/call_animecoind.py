import sys
import os

# PATH HACK
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from core_modules.blockchain import BlockChain
from core_modules.chainwrapper import ChainWrapper
from core_modules.masternode_discovery import read_settings_file


def get_blockchain(basedir):
    x = read_settings_file(basedir)
    blockchainsettings = [x["rpcuser"], x["rpcpassword"], x["ip"], x["rpcport"]]
    return BlockChain(*blockchainsettings)


def main(basedir):
    blockchain = get_blockchain(basedir)

    blockcount = blockchain.getblockcount() - 1
    for blocknum in range(1, blockcount+1):
        block = blockchain.getblock(str(blocknum))
        for tx in block["tx"]:
            print("TX", blocknum, tx)
            t = blockchain.getrawtransaction(tx, 1)
            print(t["confirmations"])


if __name__ == "__main__":
    basedir = sys.argv[1]
    main(basedir)
