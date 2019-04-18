import nacl
import hashlib

from core_modules.helpers import require_true


def __get_raw_blake2b_sha3_512_merged_hash_func(input_data):
    hash_of_input_data = hashlib.sha3_512(input_data).digest() + hashlib.blake2b(input_data).digest()
    return hash_of_input_data


def sqrt4k3(x, p):
    return pow(x, (p + 1) // 4, p)


# Compute candidate square root of x modulo p, with p = 5 (mod 8).
def sqrt8k5(x, p):
    y = pow(x, (p + 3) // 8, p)
    # If the square root exists, it is either y, or y*2^(p-1)/4.
    if (y * y) % p == x % p:
        return y
    else:
        z = pow(2, (p - 1) // 4, p)
        return (y * z) % p


# Decode a hexadecimal string representation of integer.
def hexi(s):
    return int.from_bytes(bytes.fromhex(s), byteorder="big")


# Rotate a word x by b places to the left.
def rol(x, b):
    return ((x << b) | (x >> (64 - b))) & (2 ** 64 - 1)


# From little-endian.
def from_le(s):
    return int.from_bytes(s, byteorder="little")


# A (prime) field element.
class Field:
    # Construct number x (mod p).
    def __init__(self, x, p):
        self.__x = x % p
        self.__p = p

    # Check that fields of self and y are the same.
    def __check_fields(self, y):
        if type(y) is not Field or self.__p != y.__p:
            raise ValueError("Fields don't match")

    # Field addition. The fields must match.
    def __add__(self, y):
        self.__check_fields(y)
        return Field(self.__x + y.__x, self.__p)

    # Field subtraction. The fields must match.
    def __sub__(self, y):
        self.__check_fields(y)
        return Field(self.__p + self.__x - y.__x, self.__p)

    # Field negation.
    def __neg__(self):
        return Field(self.__p - self.__x, self.__p)

    # Field multiplication. The fields must match.
    def __mul__(self, y):
        self.__check_fields(y)
        return Field(self.__x * y.__x, self.__p)

    # Field division. The fields must match.
    def __truediv__(self, y):
        return self * y.inv()

    # Field inverse (inverse of 0 is 0).
    def inv(self):
        return Field(pow(self.__x, self.__p - 2, self.__p), self.__p)

    # Field square root. Returns none if square root does not exist.
    # Note: not presently implemented for p mod 8 = 1 case.
    def sqrt(self):
        # Compute candidate square root.
        if self.__p % 4 == 3:
            y = sqrt4k3(self.__x, self.__p)
        elif self.__p % 8 == 5:
            y = sqrt8k5(self.__x, self.__p)
        else:
            raise NotImplementedError("sqrt(_,8k+1)")
        _y = Field(y, self.__p)
        # Check square root candidate valid.
        return _y if _y * _y == self else None

    # Make Field element with the same field as this, but different
    # value.
    def make(self, ival):
        return Field(ival, self.__p)

    # Is field element the additive identity?
    def iszero(self):
        return self.__x == 0

    # Are field elements equal?
    def __eq__(self, y):
        return self.__x == y.__x and self.__p == y.__p

    # Are field elements not equal?
    def __ne__(self, y):
        return not (self == y)

    # Serialize number to b-1 bits.
    def tobytes(self, b):
        return self.__x.to_bytes(b // 8, byteorder="little")

    # Unserialize number from bits.
    def frombytes(self, x, b):
        rv = from_le(x) % (2 ** (b - 1))
        return Field(rv, self.__p) if rv < self.__p else None

    # Compute sign of number, 0 or 1. The sign function
    # has the following property:
    # sign(x) = 1 - sign(-x) if x != 0.
    def sign(self):
        return self.__x % 2


# A point on (twisted) Edwards curve.
class EdwardsPoint:
    base_field = None
    x = None
    y = None
    z = None

    def initpoint(self, x, y):
        self.x = x
        self.y = y
        self.z = self.base_field.make(1)

    def decode_base(self, s, b):
        # Check that point encoding is of correct length.
        if len(s) != b // 8: return (None, None)
        # Extract signbit.
        xs = s[(b - 1) // 8] >> ((b - 1) & 7)
        # Decode y. If this fails, fail.
        y = self.base_field.frombytes(s, b)
        if y is None: return (None, None)
        # Try to recover x. If it does not exist, or is zero and xs is
        # wrong, fail.
        x = self.solve_x2(y).sqrt()
        if x is None or (x.iszero() and xs != x.sign()):
            return (None, None)
        # If sign of x isn't correct, flip it.
        if x.sign() != xs: x = -x
        # Return the constructed point.
        return (x, y)

    def encode_base(self, b):
        xp, yp = self.x / self.z, self.y / self.z
        # Encode y.
        s = bytearray(yp.tobytes(b))
        # Add sign bit of x to encoding.
        if xp.sign() != 0: s[(b - 1) // 8] |= 1 << (b - 1) % 8
        return s

    def __mul__(self, x):
        r = self.zero_elem()
        s = self
        while x > 0:
            if (x % 2) > 0:
                r = r + s
            s = s.double()
            x = x // 2
        return r

    # Check two points are equal.
    def __eq__(self, y):
        # Need to check x1/z1 == x2/z2 and similarly for y, so cross-
        # multiply to eliminate divisions.
        xn1 = self.x * y.z
        xn2 = y.x * self.z
        yn1 = self.y * y.z
        yn2 = y.y * self.z
        return xn1 == xn2 and yn1 == yn2

    # Check two points are not equal.
    def __ne__(self, y):
        return not (self == y)


class Edwards521Point(EdwardsPoint):  # By JE based on https://mojzis.com/software/eddsa/eddsa.py
    # Create a new point on curve.
    base_field = Field(1, 2 ** 521 - 1)
    d = base_field.make(-376014)
    f0 = base_field.make(0)
    f1 = base_field.make(1)
    xb = base_field.make(hexi(
        "752cb45c48648b189df90cb2296b2878a3bfd9f42fc6c818ec8bf3c9c0c6203913f6ecc5ccc72434b1ae949d568fc99c6059d0fb13364838aa302a940a2f19ba6c"))
    yb = base_field.make(hexi("0c"))  # JE: See https://safecurves.cr.yp.to/base.html

    # The standard base point.
    @staticmethod
    def stdbase():
        return Edwards521Point(Edwards521Point.xb, Edwards521Point.yb)

    def __init__(self, x, y):
        # Check the point is actually on the curve.
        if y * y + x * x != self.f1 + self.d * x * x * y * y:
            raise ValueError("Invalid point")
        self.initpoint(x, y)

    # Decode a point representation.
    def decode(self, s):
        x, y = self.decode_base(s, 528)
        return Edwards521Point(x, y) if x is not None else None

    # Encode a point representation
    def encode(self):
        return self.encode_base(528)

    # Construct neutral point on this curve.
    def zero_elem(self):
        return Edwards521Point(self.f0, self.f1)

    # Solve for x^2.
    def solve_x2(self, y):
        return ((y * y - self.f1) / (self.d * y * y - self.f1))

    # Point addition.
    def __add__(self, y):
        # The formulas are from EFD.
        tmp = self.zero_elem()
        xcp, ycp, zcp = self.x * y.x, self.y * y.y, self.z * y.z
        B = zcp * zcp
        E = self.d * xcp * ycp
        F, G = B - E, B + E
        tmp.x = zcp * F * ((self.x + self.y) * (y.x + y.y) - xcp - ycp)
        tmp.y, tmp.z = zcp * G * (ycp - xcp), F * G
        return tmp

    # Point doubling.
    def double(self):
        # The formulas are from EFD.
        tmp = self.zero_elem()
        x1s, y1s, z1s = self.x * self.x, self.y * self.y, self.z * self.z
        xys = self.x + self.y
        F = x1s + y1s
        J = F - (z1s + z1s)
        tmp.x, tmp.y, tmp.z = (xys * xys - x1s - y1s) * J, F * (x1s - y1s), F * J
        return tmp

    # Order of basepoint.
    def l(self):
        return hexi(
            "7ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd15b6c64746fc85f736b8af5e7ec53f04fbd8c4569a8f1f4540ea2435f5180d6b")

    # The logarithm of cofactor.
    def c(self): return 2

    # The highest set bit
    def n(self): return 520

    # The coding length
    def b(self): return 528

    # Validity check (for debugging)
    def is_valid_point(self):
        x, y, z = self.x, self.y, self.z
        x2 = x * x
        y2 = y * y
        z2 = z * z
        lhs = (x2 + y2) * z2
        rhs = z2 * z2 + self.d * x2 * y2
        require_true(lhs == rhs)


# PureEdDSA scheme. Limitation: Only b mod 8 = 0 is handled.
class PureEdDSA:
    # Create a new object.
    def __init__(self, properties):
        self.B = properties["B"]
        self.H = properties["H"]
        self.l = self.B.l()
        self.n = self.B.n()
        self.b = self.B.b()
        self.c = self.B.c()

    # Clamp a private scalar.
    def __clamp(self, a):
        _a = bytearray(a)
        for i in range(0, self.c): _a[i // 8] &= ~(1 << (i % 8))
        _a[self.n // 8] |= 1 << (self.n % 8)
        for i in range(self.n + 1, self.b): _a[i // 8] &= ~(1 << (i % 8))
        return _a

    # Generate a key. If privkey is None, random one is generated.
    # In any case, privkey, pubkey pair is returned.
    def keygen(self, privkey):
        # If no private key data given, generate random.
        # if privkey is None: privkey= os.urandom(self.b//8) #Replaced with more secure nacl version which uses this: https://news.ycombinator.com/item?id=11562401
        if privkey is None: privkey = nacl.utils.random(self.b // 8)
        # Expand key.
        khash = self.H(privkey, None, None)
        a = from_le(self.__clamp(khash[:self.b // 8]))
        # Return the keypair (public key is A=Enc(aB).
        return privkey, (self.B * a).encode()

    # Sign with keypair.
    def sign(self, privkey, pubkey, msg, ctx, hflag):
        # Expand key.
        khash = self.H(privkey, None, None)
        a = from_le(self.__clamp(khash[:self.b // 8]))
        seed = khash[self.b // 8:]
        # Calculate r and R (R only used in encoded form)
        r = from_le(self.H(seed + msg, ctx, hflag)) % self.l
        R = (self.B * r).encode()
        # Calculate h.
        h = from_le(self.H(R + pubkey + msg, ctx, hflag)) % self.l
        # Calculate s.
        S = ((r + h * a) % self.l).to_bytes(self.b // 8, byteorder="little")
        # The final signature is concatenation of R and S.
        return R + S

    # Verify signature with public key.
    def verify(self, pubkey, msg, sig, ctx, hflag):
        # Sanity-check sizes.
        if len(sig) != self.b // 4: return False
        if len(pubkey) != self.b // 8: return False
        # Split signature into R and S, and parse.
        Rraw, Sraw = sig[:self.b // 8], sig[self.b // 8:]
        R, S = self.B.decode(Rraw), from_le(Sraw)
        # Parse public key.
        A = self.B.decode(pubkey)
        # Check parse results.
        if (R is None) or (A is None) or S >= self.l: return False
        # Calculate h.
        h = from_le(self.H(Rraw + pubkey + msg, ctx, hflag)) % self.l
        # Calculate left and right sides of check eq.
        rhs = R + (A * h)
        lhs = self.B * S
        for i in range(0, self.c):
            lhs = lhs.double()
            rhs = rhs.double()
        # Check eq. holds?
        return lhs == rhs


# EdDSA scheme.
class EdDSA:
    # Create a new scheme object, with specified PureEdDSA base scheme and specified prehash.
    def __init__(self, pure_scheme, prehash):
        self.__pflag = True
        self.__pure = pure_scheme
        self.__prehash = prehash
        if self.__prehash is None:
            self.__prehash = lambda x, y: x
            self.__pflag = False

    # Generate a key. If privkey is none, generates a random privkey key, otherwise uses specified private key. Returns pair (privkey, pubkey).
    def keygen(self, privkey):
        return self.__pure.keygen(privkey)

    # Sign message msg using specified keypair.
    def sign(self, privkey, pubkey, msg, ctx=None):
        if ctx is None: ctx = b""
        return self.__pure.sign(privkey, pubkey, self.__prehash(msg, ctx), \
                                ctx, self.__pflag)

    # Verify signature sig on message msg using public key pubkey.
    def verify(self, pubkey, msg, sig, ctx=None):
        if ctx is None: ctx = b""
        return self.__pure.verify(pubkey, self.__prehash(msg, ctx), sig, \
                                  ctx, self.__pflag)


def Ed521_inthash(data, ctx, hflag):
    if (ctx is not None and len(ctx) > 0) or hflag:
        raise ValueError("Contexts/hashes not supported")
    return __get_raw_blake2b_sha3_512_merged_hash_func(data)


# #Simple self-check.
# def curve_self_check(point):
#     p=point
#     q=point.zero_elem()
#     z=q
#     l=p.l()+1
#     p.is_valid_point()
#     q.is_valid_point()
#     for i in range(0,point.b()):
#         if (l>>i)&1 != 0:
#             q=q+p
#             q.is_valid_point()
#         p=p.double()
#         p.is_valid_point()
#     require_true(q.encode() == point.encode())
#     require_true(q.encode() != p.encode())
#     require_true(q.encode() != z.encode())
#
# #Simple self-check.
# def self_check_curves():
#     curve_self_check(Edwards521Point.stdbase())
#
#
# def eddsa_obj(name):
#     if name == "Ed521": Ed521
#     raise NotImplementedError("Algorithm not implemented")


def get_Ed521():
    # The base PureEdDSA schemes.
    pEd521 = PureEdDSA({"B": Edwards521Point.stdbase(), "H": Ed521_inthash})

    # Our signature schemes.
    Ed521 = EdDSA(pEd521, None)
    return Ed521
