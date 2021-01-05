import hashlib
import struct
import random
import math

from struct import pack, unpack
from collections import defaultdict

from core_modules.logger import initlogging

HEADER_PATTERN = '<3I32s'
HEADER_LENGTH = struct.calcsize(HEADER_PATTERN)

luby_logger = initlogging('Lubby', __name__)


class NotEnoughChunks(Exception):
    pass


class BlockParseError(Exception):
    pass


# LT Coding Helper fucntions:
class _PRNG:
    """
    A Pseudorandom Number Generator that yields samples from the set of source
    blocks using the RSD degree distribution described above.
    """

    def __init__(self, k):
        """Provide RSD parameters on construction """
        self.state = None  # Seed is set by interfacing code using set_seed

        c = 0.1         # Don't touch
        delta = 0.5     # Don't touch

        self.K = k
        self.cdf = self.__gen_rsd_cdf(self.K, delta, c)

    def __gen_tau(self, S, K, delta):
        """The Robust part of the RSD, we precompute an array for speed"""
        pivot = int(math.floor(K / S))
        return [S / K * 1 / d for d in range(1, pivot)] \
               + [S / K * math.log(S / delta)] \
               + [0 for d in range(pivot, K)]

    def __gen_rho(self, K):
        """The Ideal Soliton Distribution, we precompute an array for speed"""
        return [1 / K] + [1 / (d * (d - 1)) for d in range(2, K + 1)]

    def __gen_mu(self, K, delta, c):
        """The Robust Soliton Distribution on the degree of transmitted blocks"""
        S = c * math.log(K / delta) * math.sqrt(K)
        tau = self.__gen_tau(S, K, delta)
        rho = self.__gen_rho(K)
        normalizer = sum(rho) + sum(tau)
        return [(rho[d] + tau[d]) / normalizer for d in range(K)]

    def __gen_rsd_cdf(self, K, delta, c):
        """The CDF of the RSD on block degree, precomputed for sampling speed"""
        mu = self.__gen_mu(K, delta, c)
        return [sum(mu[:d + 1]) for d in range(K)]


    def _get_next(self):
        """Executes the next iteration of the PRNG evolution process, and returns the result"""
        PRNG_A = 16807
        PRNG_M = (1 << 31) - 1
        self.state = PRNG_A * self.state % PRNG_M
        return self.state

    def _sample_d(self):
        """Samples degree given the precomputed distributions above and the linear PRNG output """
        PRNG_M = (1 << 31) - 1
        PRNG_MAX_RAND = PRNG_M - 1
        p = self._get_next() / PRNG_MAX_RAND
        for ix, v in enumerate(self.cdf):
            if v > p:
                return ix + 1
        return ix + 1

    def set_seed(self, seed):
        """Reset the state of the PRNG to the given seed"""
        self.state = seed

    def get_src_blocks(self, seed=None):
        """
        Returns the indices of a set of `d` source blocks sampled from indices i = 1, ..., K-1 uniformly,
        where `d` is sampled from the RSD described above.
        """
        if seed:
            self.state = seed
        blockseed = self.state
        d = self._sample_d()
        have = 0
        nums = set()
        while have < d:
            num = self._get_next() % self.K
            if num not in nums:
                nums.add(num)
                have += 1
        return blockseed, d, nums


class _CheckNode:
    def __init__(self, src_nodes, check):
        self.check = check
        self.src_nodes = src_nodes


class _BlockGraph:
    """Graph on which we run Belief Propagation to resolve source node data"""

    def __init__(self, num_blocks):
        self.checks = defaultdict(list)
        self.num_blocks = num_blocks
        self.eliminated = {}

    def add_block(self, nodes, data):
        """
        Adds a new check node and edges between that node and all source nodes it connects,
        resolving all message passes that become possible as a result.
        """
        if len(nodes) == 1:  # We can eliminate this source node
            to_eliminate = list(self.eliminate(next(iter(nodes)), data))
            while len(to_eliminate):  # Recursively eliminate all nodes that can now be resolved
                other, check = to_eliminate.pop()
                to_eliminate.extend(self.eliminate(other, check))
        else:
            for node in list(nodes):  # Pass messages from already-resolved source nodes
                if node in self.eliminated:
                    nodes.remove(node)
                    data ^= self.eliminated[node]
            if len(nodes) == 1:  # Resolve if we are left with a single non-resolved source node
                return self.add_block(nodes, data)
            else:  # Add edges for all remaining nodes to this check
                check = _CheckNode(nodes, data)
                for node in nodes:
                    self.checks[node].append(check)
        return len(self.eliminated) >= self.num_blocks  # Are we done yet?

    def eliminate(self, node, data):
        """Resolves a source node, passing the message to all associated checks """
        self.eliminated[node] = data  # Cache resolved value
        others = self.checks[node]
        del self.checks[node]
        for check in others:  # Pass messages to all associated checks
            check.check ^= data
            check.src_nodes.remove(node)
            if len(check.src_nodes) == 1:  # Yield all nodes that can now be resolved
                yield (next(iter(check.src_nodes)), check.check)


def encode(redundancy_factor, end_block_size, data, seeds=None):
    """
    Encode image with given `data` into number of chunks, using provided redundancy_factor and block size.
    Use provided seeds, or generate random ones.
    """
    block_size = end_block_size - HEADER_LENGTH
    total_blocks = math.ceil((1.00 * redundancy_factor * len(data)) / block_size)

    blocks = []
    for i in range(0, len(data), block_size):
        # zero pad
        x = data[i:i+block_size].ljust(block_size, b'0')
        tmp = int.from_bytes(x, 'little')
        blocks.append(tmp)

    prng = _PRNG(len(blocks))

    if seeds is None:
        seed = random.randint(0, 2**30)
        prng.set_seed(seed)

    luby_blocks = []
    count = 0
    while len(luby_blocks) < total_blocks:
        seed = seeds[count] if seeds else None
        seed, d, ix_samples = prng.get_src_blocks(seed=seed)
        block_data = 0
        for ix in ix_samples:
            block_data ^= blocks[ix]
        block_data_bytes = int.to_bytes(block_data, block_size, 'little')
        block_hash = hashlib.sha3_256(block_data_bytes).digest()
        block = (len(data), block_size, seed, block_hash, block_data_bytes)

        bit_packing_pattern_string = HEADER_PATTERN + str(block_size) + 's'

        packed_block_data = pack(bit_packing_pattern_string, *block)
        luby_blocks.append(packed_block_data)
        count += 1
    return luby_blocks


def __parse_block(block):
    # parse block header
    if len(block) < HEADER_LENGTH:
        raise BlockParseError("Not enough data in block: %s!" % len(block))

    header_data = block[:HEADER_LENGTH]
    data_length, block_size, seed, block_hash = unpack(HEADER_PATTERN, header_data)

    # parse block body
    if len(block) < HEADER_LENGTH + block_size:
        raise BlockParseError("Not enough data in block: %s!" % len(block))

    block_body = block[HEADER_LENGTH:HEADER_LENGTH + block_size]
    return data_length, block_size, seed, block_hash, block_body


def get_seeds(blocks):
    """
    Parse each block and return list of its seeds. Order is important to reconstruct image properly.
    """
    seeds = []
    for block in blocks:
        data_length, block_size, seed, block_hash, block_body = __parse_block(block)
        seeds.append(seed)
    return seeds


def verify_blocks(blocks):
    seeds = set()
    blocksizes = set()
    datalengths = set()
    for block in blocks:
        data_length, block_size, seed, block_hash, block_body = __parse_block(block)

        seeds.add(seed)
        datalengths.add(data_length)
        blocksizes.add(block_size)

    if len(seeds) != len(blocks):
        raise ValueError("Number of seeds does not match number of blocks!")

    if len(datalengths) != 1:
        raise ValueError("Data length is not the same across blocks!")

    if len(blocksizes) != 1:
        raise ValueError("Block sizes are not the same across blocks!")


def decode(blocks):
    minimum_required, block_graph, prng = None, None, None
    done = False
    for block_count, block in enumerate(blocks):
        # TODO: instead of printing errors log these properly!
        # parse block
        try:
            data_length, block_size, seed, block_hash, block_body = __parse_block(block)
        except BlockParseError as exc:
            luby_logger.warn("Block parsing failed with exception: %s" % exc)
            continue

        # we need to at least find one block that we can parse to calculate minimum_required
        if block_graph is None:
            minimum_required = math.ceil(data_length / block_size)
            block_graph = _BlockGraph(minimum_required)
            prng = _PRNG(minimum_required)

        # make sure block hash matches
        calculated_hash = hashlib.sha3_256(block_body).digest()
        if calculated_hash != block_hash:
            luby_logger.warn("Header body hash is corrupted!")
            continue

        # decode the block
        _, _, src_blocks = prng.get_src_blocks(seed=seed)
        block_data_bytes_decoded = int.from_bytes(block_body, 'little')
        done = block_graph.add_block(src_blocks, block_data_bytes_decoded)
        if done:
            break

    if not done:
        raise NotEnoughChunks("Not enough Luby blocks to reconstruct file!")

    ret = bytearray()
    sorted_nodes = sorted(block_graph.eliminated.items(), key=lambda p: p[0])
    for i, node in enumerate(sorted_nodes):
        block_bytes = int.to_bytes(node[1], block_size, 'little')

        if (i < minimum_required - 1) or ((data_length % block_size) == 0):
            ret += block_bytes
        else:
            ret += block_bytes[:data_length % block_size]

    return ret
