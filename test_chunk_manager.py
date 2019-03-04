import os
import sys
import random
import uuid
import asyncio
import zmq
import zmq.asyncio

from datetime import datetime as dt

from masternode_prototype.masternode_logic import MasterNodeLogic
from core_modules.helpers import get_nodeid_from_pubkey, getrandbytes
from core_modules.blackbox_modules.keys import id_keypair_generation_func


async def heartbeat():
    while True:
        print("HB", dt.now())
        await asyncio.sleep(1)


async def send_rpc_to_random_mn(masternode_list, myid):
    SLEEPTIME = 1
    ctx = zmq.asyncio.Context()
    sockets = {}
    while True:
        nodeid, ip, port, pubkey = random.choice(masternode_list)
        print("%s Sending request to MN: %s" % (myid, nodeid))

        if sockets.get(nodeid) is None:
            sock = ctx.socket(zmq.DEALER)
            sock.setsockopt(zmq.IDENTITY, bytes(str(uuid.uuid4()), "utf-8"))
            sock.connect("tcp://%s:%s" % (ip, port))
            sockets[nodeid] = sock

        sock = sockets[nodeid]
        start = dt.now()
        await sock.send_multipart([b'PING'])

        print("%s Sent request to MN: %s, waiting for reply" % (myid, nodeid))
        msg = await sock.recv_multipart()  # waits for msg to be ready
        stop = dt.now()
        elapsed = (stop-start).total_seconds()

        print("%s Received reply: %s from %s in %ss, sleeping for %ss" % (myid, msg, nodeid, elapsed, SLEEPTIME))
        await asyncio.sleep(SLEEPTIME)


def generate_masternodes(num_mn, ip, port):
    ret = []
    for i in range(num_mn):
        privkey, pubkey = id_keypair_generation_func()
        mn = (get_nodeid_from_pubkey(getrandbytes(1024)), ip, port + i, privkey, pubkey)
        ret.append(mn)
    return ret


if __name__ == "__main__":
    NUM_MN = 2

    basedir = sys.argv[1]
    test_chunks = sys.argv[2]

    masternode_list = generate_masternodes(NUM_MN, "127.0.0.1", 86752)

    # we can use this to generate chunks, but right now we use the pregenerated test chunks
    # NUM_CHUNKS = 1000
    # CHUNK_SIZE = 1024*1024
    # chunks = [(chunkid_to_hex(k), v) for k,v in generate_chunks(NUM_CHUNKS, CHUNK_SIZE).items()]

    # read test chunks from disk
    chunks = []
    for i in os.listdir(test_chunks)[:10]:
        k, v = i, open(os.path.join(test_chunks, i), "rb").read()
        chunks.append((k, v))
    print("Read %s chunks from testdir" % len(chunks))

    # spawn masternodes
    masternodes = []
    for i, config in enumerate(masternode_list):
        name = "mn_%s" % i
        chunkdir = os.path.join(basedir, name)
        os.makedirs(chunkdir, exist_ok=True)

        nodeid, ip, port, privkey, pubkey = config

        mn = MasterNodeLogic(name=name,
                             basedir=chunkdir,
                             privkey=privkey,
                             pubkey=pubkey,
                             ip=ip,
                             port=port,
                             chunks=[x[0] for x in chunks])

        masternodes.append(mn)

    # load full chunks only on the first masternode
    masternodes[0].load_full_chunks(chunks)

    # start async loops
    loop = asyncio.get_event_loop()
    for mn in masternodes:
        loop.create_task(mn.zmq_run_forever())

    loop.create_task(heartbeat())

    for mn in masternodes:
        loop.create_task(mn.issue_random_tests_forever(1))
        loop.create_task(mn.run_chunk_fetcher_forever())

    loop.run_forever()

    # input("Waiting for keypress: ")
    # for mn in masternodes:
    #     mn.update_mn_list(masternode_list[1:])
    #
    # input("Waiting for keypress: ")
    # newchunk = "42ad07fac0678fa2bac61b0255646ec960dee1bf2b646c88c07fb791c365d3a3"
    # for mn in masternodes:
    #     mn.new_chunks_added_to_blockchain([newchunk])
    #
    # for mn in masternodes:
    #     owner = mn.get_chunk_ownership("42ad07fac0678fa2bac61b0255646ec960dee1bf2b646c88c07fb791c365d3a3")
    #     print("MN %s, owner: %s" % (mn, owner))
