import sys
import os
import hashlib

from datetime import datetime as dt, timedelta as td

# PATH HACK
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from core_modules.helpers import get_cnode_digest_bytes, getrandbytes

HASHLISTSIZE = 1000*1000*10
HASH_ENTRY_SIZE = 32

print("[+] Building hashlist")
hashlist = []
for i in range(HASHLISTSIZE):
    hashlist.append(getrandbytes(HASH_ENTRY_SIZE))

algos = sorted(hashlib.algorithms_guaranteed)
print("[+] Testing %s entries of %s size" % (HASHLISTSIZE, HASH_ENTRY_SIZE))
print("[+] Testing hash algorithms: %s" % algos)
for algo in algos:
    # shake has variable length digests, ignore it
    if algo.startswith('shake_'):
        continue

    algo_class = getattr(hashlib, algo)
    start = dt.now()
    ret = list(map(lambda x: algo_class(x).digest(), hashlist))
    end = dt.now()

    total_time = (end-start).total_seconds()
    print("  [+] Algo %s in %.2f -> %.2f MB/s" % (algo, total_time, (HASHLISTSIZE*HASH_ENTRY_SIZE/1024/1024)/total_time))
print("[+] Done")
