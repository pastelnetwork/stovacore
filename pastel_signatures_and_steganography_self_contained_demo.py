import time, base64, hashlib, random, os, io, math, glob
from time import sleep
from datetime import datetime
import nacl.encoding
import nacl.signing
import nacl.secret
import nacl.utils
import pyqrcode
import pyotp
from PIL import Image, ImageFont, ImageDraw, ImageOps
import numpy as np

# Dependencies:
# pip install nacl pyqrcode pypng
#Eddsa code is from the RFC documentation: https://datatracker.ietf.org/doc/html/rfc8032

class MyTimer():
    def __init__(self):
        self.start = time.time()
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        end = time.time()
        runtime = end - self.start
        msg = '({time} seconds to complete)'
        print(msg.format(time=round(runtime,5)))
        
def get_blake2b_sha3_512_merged_hash_func(input_data_or_string):
    if isinstance(input_data_or_string, str):
        input_data_or_string = input_data_or_string.encode('utf-8')
    hash_of_input_data = hashlib.sha3_512(input_data_or_string).hexdigest() + hashlib.blake2b(input_data_or_string).hexdigest()
    return hash_of_input_data

def get_raw_blake2b_sha3_512_merged_hash_func(input_data):
    hash_of_input_data = hashlib.sha3_512(input_data).digest() + hashlib.blake2b(input_data).digest()
    return hash_of_input_data

def sqrt4k3(x,p): 
    return pow(x,(p + 1)//4,p)

#Compute candidate square root of x modulo p, with p = 5 (mod 8).
def sqrt8k5(x,p):
    y = pow(x,(p+3)//8,p)
    #If the square root exists, it is either y, or y*2^(p-1)/4.
    if (y * y) % p == x % p: return y
    else:
        z = pow(2,(p - 1)//4,p)
        return (y * z) % p

#Decode a hexadecimal string representation of integer.
def hexi(s): 
    return int.from_bytes(bytes.fromhex(s), byteorder="big")

#Rotate a word x by b places to the left.
def rol(x,b): 
    return ((x << b) | (x >> (64 - b))) & (2**64-1)

#From little-endian.
def from_le(s): 
    return int.from_bytes(s, byteorder="little")

#A (prime) field element. 
class Field:
    #Construct number x (mod p).
    def __init__(self,x,p):
        self.__x=x%p
        self.__p=p
    #Check that fields of self and y are the same.
    def __check_fields(self,y):
        if type(y) is not Field or self.__p!=y.__p:
            raise ValueError("Fields don't match")
    #Field addition. The fields must match.
    def __add__(self,y):
        self.__check_fields(y)
        return Field(self.__x+y.__x,self.__p)
    #Field subtraction. The fields must match.
    def __sub__(self,y):
        self.__check_fields(y)
        return Field(self.__p+self.__x-y.__x,self.__p)
    #Field negation.
    def __neg__(self):
        return Field(self.__p-self.__x,self.__p)
    #Field multiplication. The fields must match.
    def __mul__(self,y):
        self.__check_fields(y)
        return Field(self.__x*y.__x,self.__p)
    #Field division. The fields must match.
    def __truediv__(self,y):
        return self*y.inv()
    #Field inverse (inverse of 0 is 0).
    def inv(self):
        return Field(pow(self.__x,self.__p-2,self.__p),self.__p)
    #Field square root. Returns none if square root does not exist.
    #Note: not presently implemented for p mod 8 = 1 case.
    def sqrt(self):
        #Compute candidate square root.
        if self.__p%4==3: y=sqrt4k3(self.__x,self.__p)
        elif self.__p%8==5: y=sqrt8k5(self.__x,self.__p)
        else: raise NotImplementedError("sqrt(_,8k+1)")
        _y=Field(y,self.__p)
        #Check square root candidate valid.
        return _y if _y*_y==self else None
    #Make Field element with the same field as this, but different
    #value.
    def make(self,ival): return Field(ival,self.__p)
    #Is field element the additive identity?
    def iszero(self): return self.__x==0
    #Are field elements equal?
    def __eq__(self,y): return self.__x==y.__x and self.__p==y.__p
    #Are field elements not equal?
    def __ne__(self,y): return not (self==y)
    #Serialize number to b-1 bits.
    def tobytes(self,b):
        return self.__x.to_bytes(b//8,byteorder="little")
    #Unserialize number from bits.
    def frombytes(self,x,b):
        rv=from_le(x)%(2**(b-1))
        return Field(rv,self.__p) if rv<self.__p else None
    #Compute sign of number, 0 or 1. The sign function
    #has the following property:
    #sign(x) = 1 - sign(-x) if x != 0.
    def sign(self): return self.__x%2

#A point on (twisted) Edwards curve.
class EdwardsPoint:
    base_field = None
    x = None
    y = None
    z = None
    def initpoint(self, x, y):
        self.x=x
        self.y=y
        self.z=self.base_field.make(1)
    def decode_base(self,s,b):
        #Check that point encoding is of correct length.
        if len(s)!=b//8: return (None,None)
        #Extract signbit.
        xs=s[(b-1)//8]>>((b-1)&7)
        #Decode y. If this fails, fail.
        y = self.base_field.frombytes(s,b)
        if y is None: return (None,None)
        #Try to recover x. If it does not exist, or is zero and xs is
        #wrong, fail.
        x=self.solve_x2(y).sqrt()
        if x is None or (x.iszero() and xs!=x.sign()):
            return (None,None)
        #If sign of x isn't correct, flip it.
        if x.sign()!=xs: x=-x
        # Return the constructed point.
        return (x,y)
    def encode_base(self,b):
        xp,yp=self.x/self.z,self.y/self.z
        #Encode y.
        s=bytearray(yp.tobytes(b))
        #Add sign bit of x to encoding.
        if xp.sign()!=0: s[(b-1)//8]|=1<<(b-1)%8
        return s
    def __mul__(self,x):
        r=self.zero_elem()
        s=self
        while x > 0:
            if (x%2)>0:
                r=r+s
            s=s.double()
            x=x//2
        return r
    #Check two points are equal.
    def __eq__(self,y):
        #Need to check x1/z1 == x2/z2 and similarly for y, so cross-
        #multiply to eliminate divisions.
        xn1=self.x*y.z
        xn2=y.x*self.z
        yn1=self.y*y.z
        yn2=y.y*self.z
        return xn1==xn2 and yn1==yn2
    #Check two points are not equal.
    def __ne__(self,y): return not (self==y)
    

class Edwards521Point(EdwardsPoint): #By JE based on https://mojzis.com/software/eddsa/eddsa.py
    #Create a new point on curve.
    base_field=Field(1,2**521 - 1)
    d=base_field.make(-376014)
    f0=base_field.make(0)
    f1=base_field.make(1)
    xb=base_field.make(hexi("752cb45c48648b189df90cb2296b2878a3bfd9f42fc6c818ec8bf3c9c0c6203913f6ecc5ccc72434b1ae949d568fc99c6059d0fb13364838aa302a940a2f19ba6c"))
    yb=base_field.make(hexi("0c")) # JE: See https://safecurves.cr.yp.to/base.html
    #The standard base point.
    @staticmethod
    def stdbase():
        return Edwards521Point(Edwards521Point.xb, Edwards521Point.yb)
    def __init__(self,x,y):
        #Check the point is actually on the curve.
        if y*y+x*x!=self.f1+self.d*x*x*y*y:
            raise ValueError("Invalid point")
        self.initpoint(x, y)
    #Decode a point representation.
    def decode(self,s):
        x,y=self.decode_base(s,528)
        return Edwards521Point(x, y) if x is not None else None
    #Encode a point representation
    def encode(self):
        return self.encode_base(528)
    #Construct neutral point on this curve.
    def zero_elem(self):
        return Edwards521Point(self.f0,self.f1)
    #Solve for x^2.
    def solve_x2(self,y):
        return ((y*y-self.f1)/(self.d*y*y-self.f1))
    #Point addition.
    def __add__(self,y):
        #The formulas are from EFD.
        tmp=self.zero_elem()
        xcp,ycp,zcp=self.x*y.x,self.y*y.y,self.z*y.z
        B=zcp*zcp
        E=self.d*xcp*ycp
        F,G=B-E,B+E
        tmp.x=zcp*F*((self.x+self.y)*(y.x+y.y)-xcp-ycp)
        tmp.y,tmp.z=zcp*G*(ycp-xcp),F*G
        return tmp
    #Point doubling.
    def double(self):
        #The formulas are from EFD.
        tmp=self.zero_elem()
        x1s,y1s,z1s=self.x*self.x,self.y*self.y,self.z*self.z
        xys=self.x+self.y
        F=x1s+y1s
        J=F-(z1s+z1s)
        tmp.x,tmp.y,tmp.z=(xys*xys-x1s-y1s)*J,F*(x1s-y1s),F*J
        return tmp
    #Order of basepoint.
    def l(self):
        return hexi("7ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffd15b6c64746fc85f736b8af5e7ec53f04fbd8c4569a8f1f4540ea2435f5180d6b")
    #The logarithm of cofactor.
    def c(self): return 2
    #The highest set bit
    def n(self): return 520
    #The coding length
    def b(self): return 528
    #Validity check (for debugging)
    def is_valid_point(self):
        x,y,z=self.x,self.y,self.z
        x2=x*x
        y2=y*y
        z2=z*z
        lhs=(x2+y2)*z2
        rhs=z2*z2+self.d*x2*y2
        assert(lhs == rhs)


#Simple self-check.
def curve_self_check(point):
    p=point
    q=point.zero_elem()
    z=q
    l=p.l()+1
    p.is_valid_point()
    q.is_valid_point()
    for i in range(0,point.b()):
        if (l>>i)&1 != 0:
            q=q+p
            q.is_valid_point()
        p=p.double()
        p.is_valid_point()
    assert q.encode() == point.encode()
    assert q.encode() != p.encode()
    assert q.encode() != z.encode()

#Simple self-check.
def self_check_curves():
    curve_self_check(Edwards521Point.stdbase())

#PureEdDSA scheme. Limitation: Only b mod 8 = 0 is handled.
class PureEdDSA:
    #Create a new object.
    def __init__(self,properties):
        self.B=properties["B"]
        self.H=properties["H"]
        self.l=self.B.l()
        self.n=self.B.n()
        self.b=self.B.b()
        self.c=self.B.c()
    #Clamp a private scalar.
    def __clamp(self,a):
        _a = bytearray(a)
        for i in range(0,self.c): _a[i//8]&=~(1<<(i%8))
        _a[self.n//8]|=1<<(self.n%8)
        for i in range(self.n+1,self.b): _a[i//8]&=~(1<<(i%8))
        return _a
    #Generate a key. If privkey is None, random one is generated.
    #In any case, privkey, pubkey pair is returned.
    def keygen(self,privkey):
        #If no private key data given, generate random.
        #if privkey is None: privkey= os.urandom(self.b//8) #Replaced with more secure nacl version which uses this: https://news.ycombinator.com/item?id=11562401
        if privkey is None: privkey= nacl.utils.random(self.b//8)
        #Expand key.
        khash=self.H(privkey,None,None)
        a=from_le(self.__clamp(khash[:self.b//8]))
        #Return the keypair (public key is A=Enc(aB).
        return privkey,(self.B*a).encode()
    #Sign with keypair.
    def sign(self,privkey,pubkey,msg,ctx,hflag):
        #Expand key.
        khash=self.H(privkey,None,None)
        a=from_le(self.__clamp(khash[:self.b//8]))
        seed=khash[self.b//8:]
        #Calculate r and R (R only used in encoded form)
        r=from_le(self.H(seed+msg,ctx,hflag))%self.l
        R=(self.B*r).encode()
        #Calculate h.
        h=from_le(self.H(R+pubkey+msg,ctx,hflag))%self.l
        #Calculate s.
        S=((r+h*a)%self.l).to_bytes(self.b//8,byteorder="little")
        #The final signature is concatenation of R and S.
        return R+S
    #Verify signature with public key.
    def verify(self,pubkey,msg,sig,ctx,hflag):
        #Sanity-check sizes.
        if len(sig)!=self.b//4: return False
        if len(pubkey)!=self.b//8: return False
        #Split signature into R and S, and parse.
        Rraw,Sraw=sig[:self.b//8],sig[self.b//8:]
        R,S=self.B.decode(Rraw),from_le(Sraw)
        #Parse public key.
        A=self.B.decode(pubkey)
        #Check parse results.
        if (R is None) or (A is None) or S>=self.l: return False
        #Calculate h.
        h=from_le(self.H(Rraw+pubkey+msg,ctx,hflag))%self.l
        #Calculate left and right sides of check eq.
        rhs=R+(A*h)
        lhs=self.B*S
        for i in range(0, self.c):
            lhs = lhs.double()
            rhs = rhs.double()
        #Check eq. holds?
        return lhs==rhs
    
def Ed521_inthash(data, ctx, hflag):
    if (ctx is not None and len(ctx) > 0) or hflag:
        raise ValueError("Contexts/hashes not supported")
    return get_raw_blake2b_sha3_512_merged_hash_func(data)


#EdDSA scheme.
class EdDSA:
    #Create a new scheme object, with specified PureEdDSA base scheme and specified prehash.
    def __init__(self,pure_scheme,prehash):
        self.__pflag = True
        self.__pure=pure_scheme
        self.__prehash=prehash
        if self.__prehash is None:
            self.__prehash = lambda x,y:x
            self.__pflag = False
    # Generate a key. If privkey is none, generates a random privkey key, otherwise uses specified private key. Returns pair (privkey, pubkey).
    def keygen(self,privkey): return self.__pure.keygen(privkey)
    # Sign message msg using specified keypair.
    def sign(self,privkey,pubkey,msg,ctx=None):
        if ctx is None: ctx=b""
        return self.__pure.sign(privkey,pubkey,self.__prehash(msg,ctx),\
            ctx,self.__pflag)
    # Verify signature sig on message msg using public key pubkey.
    def verify(self,pubkey,msg,sig,ctx=None):
        if ctx is None: ctx=b""
        return self.__pure.verify(pubkey,self.__prehash(msg,ctx),sig,\
            ctx,self.__pflag)

#The base PureEdDSA schemes.
pEd521 = PureEdDSA({"B":Edwards521Point.stdbase(),"H":Ed521_inthash})

#Our signature schemes.
Ed521 = EdDSA(pEd521, None)

def eddsa_obj(name):
    if name == "Ed521": Ed521
    raise NotImplementedError("Algorithm not implemented")

def pastel_id_keypair_generation_func():
    print('\nGenerating Eddsa 521 keypair now...')
    with MyTimer():
        input_length = 521*2
        pastel_id_private_key, pastel_id_public_key = Ed521.keygen(nacl.utils.random(input_length))
        pastel_id_private_key_b16_encoded = base64.b16encode(pastel_id_private_key).decode('utf-8')
        pastel_id_public_key_b16_encoded = base64.b16encode(pastel_id_public_key).decode('utf-8')
        return pastel_id_private_key_b16_encoded, pastel_id_public_key_b16_encoded

def pastel_id_write_signature_on_data_func(input_data_or_string, pastel_id_private_key_b16_encoded, pastel_id_public_key_b16_encoded):
   print('\nGenerating Eddsa 521 signature now...')
   with MyTimer():
       if isinstance(input_data_or_string, str):
           input_data_or_string = input_data_or_string.encode('utf-8')
       pastel_id_private_key = base64.b16decode(pastel_id_private_key_b16_encoded)
       pastel_id_public_key = base64.b16decode(pastel_id_public_key_b16_encoded)
       sleep(0.1*random.random()) #To combat side-channel attacks
       pastel_id_signature = Ed521.sign(pastel_id_private_key, pastel_id_public_key, input_data_or_string)
       pastel_id_signature_b16_encoded = base64.b16encode(pastel_id_signature).decode('utf-8')
       sleep(0.1*random.random())
       return pastel_id_signature_b16_encoded

def pastel_id_verify_signature_with_public_key_func(input_data_or_string, pastel_id_signature_b16_encoded, pastel_id_public_key_b16_encoded):
    print('\nVerifying Eddsa 521 signature now...')
    with MyTimer():
        if isinstance(input_data_or_string, str):
            input_data_or_string = input_data_or_string.encode('utf-8')
        pastel_id_signature = base64.b16decode(pastel_id_signature_b16_encoded)
        pastel_id_public_key = base64.b16decode(pastel_id_public_key_b16_encoded)
        sleep(0.1*random.random())
        verified = Ed521.verify(pastel_id_public_key, input_data_or_string, pastel_id_signature)
        sleep(0.1*random.random())
        if verified:
            print('Signature is valid!')
        else:
            print('Warning! Signature was NOT valid!')
        return verified

def set_up_google_authenticator_for_private_key_encryption_func():
    secret = pyotp.random_base32() # returns a 16 character base32 secret. Compatible with Google Authenticator and other OTP apps
    os.environ['PASTEL_OTP_SECRET'] = secret
    with open('otp_secret.txt','w') as f:
        f.write(secret)
    totp = pyotp.totp.TOTP(secret)
    #google_auth_uri = urllib.parse.quote_plus(totp.provisioning_uri("user@domain.com", issuer_name="pastel"))
    print('\nThis is you Google Authenticor Secret: ' + secret)
    google_auth_uri = totp.provisioning_uri("user@user.com", issuer_name="pastel")
    #current_otp = totp.now() 
    qr_error_correcting_level = 'M' # L, M, Q, H
    qr_encoding_type = 'binary'
    qr_scale_factor = 6
    google_auth_qr_code = pyqrcode.create(google_auth_uri, error=qr_error_correcting_level, version=16, mode=qr_encoding_type)    
    google_auth_qr_code_png_string = google_auth_qr_code.png_as_base64_str(scale=qr_scale_factor)
    google_auth_qr_code_png_data = base64.b64decode(google_auth_qr_code_png_string)
    pil_qr_code_image = Image.open(io.BytesIO(google_auth_qr_code_png_data))
    img_width, img_height = pil_qr_code_image.size #getting the base image's size
    if pil_qr_code_image.mode != 'RGB':
        pil_qr_code_image = pil_qr_code_image.convert("RGB")
    pil_qr_code_image = ImageOps.expand(pil_qr_code_image, border=(600,300,600,0))
    drawing_context = ImageDraw.Draw(pil_qr_code_image)
    font1 = ImageFont.truetype('arial.ttf', 28)
    font2 = ImageFont.truetype('arial.ttf', 22)
    warning_message = 'You should take a picture of this screen on your phone, but make sure your camera roll is secure first!\nYou can also write down your Google Auth URI string (shown below) as a backup, which will allow you to regenerate the QR code image.\n\n'
    drawing_context.text((50,65), google_auth_uri,(255,255,255),font=font1) 
    drawing_context.text((50,5), warning_message,(255,255,255),font=font2) 
    pil_qr_code_image.save('Google_Authenticator_QR_Code.png')
    print('Generated Image with Google Authenticator QR Saved to current working directory!')
    pil_qr_code_image.show()

def regenerate_google_auth_qr_code_from_secret_func():
    otp_secret = input('Enter your Google Authenticator Secret in all upper case and numbers:\n')
    otp_secret_character_set = 'ABCDEF1234567890'
    #assert(len(otp_secret)==16)
    assert([(x in otp_secret_character_set) for x in otp_secret])
    totp = pyotp.totp.TOTP(otp_secret)
    google_auth_uri = totp.provisioning_uri("user@user.com", issuer_name="pastel")
    qr_error_correcting_level = 'M' # L, M, Q, H
    qr_encoding_type = 'binary'
    qr_scale_factor = 6
    google_auth_qr_code = pyqrcode.create(google_auth_uri, error=qr_error_correcting_level, version=16, mode=qr_encoding_type)    
    google_auth_qr_code_png_string = google_auth_qr_code.png_as_base64_str(scale=qr_scale_factor)
    google_auth_qr_code_png_data = base64.b64decode(google_auth_qr_code_png_string)
    pil_qr_code_image = Image.open(io.BytesIO(google_auth_qr_code_png_data))
    pil_qr_code_image.show()
    return otp_secret

def generate_current_otp_string_from_user_input_func():
    otp_secret = input('\n\nEnter your Google Authenticator Secret in all upper case and numbers:\n\n')
    otp_secret_character_set = 'ABCDEF1234567890'
    assert(len(otp_secret)==16)
    assert([(x in otp_secret_character_set) for x in otp_secret])
    totp = pyotp.totp.TOTP(otp_secret)
    current_otp = totp.now()
    return current_otp

def generate_current_otp_string_func():
    try:
        otp_secret = os.environ['PASTEL_OTP_SECRET']
    except:
        with open('otp_secret.txt','r') as f:
            otp_secret = f.read()    
    otp_secret_character_set = 'ABCDEF1234567890'
    #assert(len(otp_secret)==16)
    assert([(x in otp_secret_character_set) for x in otp_secret])
    totp = pyotp.totp.TOTP(otp_secret)
    current_otp = totp.now()
    return current_otp

def generate_and_store_key_for_nacl_box_func():
    box_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)  # This must be kept secret, this is the combination to your safe
    box_key_base64 = base64.b64encode(box_key).decode('utf-8')
    with open('box_key.bin','w') as f:
        f.write(box_key_base64)
    print('\nThis is the key for encrypting the pastel ID private key (using NACL box) in Base64: '+ box_key_base64)
    print('\nThe key has been saved as a file in the working directory. You should also write this key down as a backup.')
    os.environ['NACL_KEY'] = box_key_base64

def get_nacl_box_key_from_user_input_func():
    box_key_base64 = input('\n\nEnter your NACL box key in Base64:\n\n')
    assert(len(box_key_base64)==44)
    box_key = base64.b64decode(box_key_base64)
    return box_key


def get_nacl_box_key_from_file_func(box_key_file_path):
    with open(box_key_file_path,'r') as f:
            box_key_base64 = f.read()
    assert(len(box_key_base64)==44)
    box_key = base64.b64decode(box_key_base64)
    return box_key

def write_pastel_public_and_private_key_to_file_func(pastel_id_public_key_b16_encoded, pastel_id_private_key_b16_encoded, box_key_file_path):
    #use_nacl_box_encryption = 1
    pastel_id_public_key_export_format = "-----BEGIN ED521 PUBLIC KEY-----\n" + pastel_id_public_key_b16_encoded + "\n-----END ED521 PUBLIC KEY-----"
    pastel_id_private_key_export_format = "-----BEGIN ED521 PRIVATE KEY-----\n" + pastel_id_private_key_b16_encoded + "\n-----END ED521 PRIVATE KEY-----"
    box_key = get_nacl_box_key_from_file_func(box_key_file_path)
    box = nacl.secret.SecretBox(box_key) # This is your safe, you can use it to encrypt or decrypt messages
    pastel_id_private_key_export_format__encrypted = box.encrypt(pastel_id_private_key_export_format.encode('utf-8'))
    pastel_id_keys_storage_folder_path = os.getcwd() + os.sep + 'pastel_id_key_files' + os.sep
    if not os.path.isdir(pastel_id_keys_storage_folder_path):
        try:
            os.makedirs(pastel_id_keys_storage_folder_path)
        except:
            print('Error creating directory-- instead saving to current working directory!')
            pastel_id_keys_storage_folder_path = os.getcwd() + os.sep
    with open(pastel_id_keys_storage_folder_path + 'pastel_id_ed521_public_key.pem','w') as f:
        f.write(pastel_id_public_key_export_format)
    with open(pastel_id_keys_storage_folder_path + 'pastel_id_ed521_private_key.pem','wb') as f:
        f.write(pastel_id_private_key_export_format__encrypted)
        
def import_pastel_public_and_private_keys_from_pem_files_func(use_require_otp, box_key_file_path):
    #use_require_otp = 1
    pastel_id_keys_storage_folder_path = os.getcwd() + os.sep + 'pastel_id_key_files' + os.sep
    if not os.path.isdir(pastel_id_keys_storage_folder_path):
        print("Can't find key storage directory, trying to use current working directory instead!")
        pastel_id_keys_storage_folder_path = os.getcwd() + os.sep
    pastel_id_public_key_pem_filepath = pastel_id_keys_storage_folder_path + 'pastel_id_ed521_public_key.pem'
    pastel_id_private_key_pem_filepath = pastel_id_keys_storage_folder_path + 'pastel_id_ed521_private_key.pem'
    if (os.path.isfile(pastel_id_public_key_pem_filepath) and os.path.isfile(pastel_id_private_key_pem_filepath)):
        with open(pastel_id_public_key_pem_filepath,'r') as f:
            pastel_id_public_key_export_format = f.read()
        with open(pastel_id_private_key_pem_filepath,'rb') as f:
            pastel_id_private_key_export_format__encrypted = f.read()
        if use_require_otp:
            try:
                otp_string = generate_current_otp_string_func()
            except:
                otp_string = generate_current_otp_string_from_user_input_func()
            otp_from_user_input = input('\nPlease Enter your pastel Google Authenticator Code:\n\n')
            assert(len(otp_from_user_input)==6)
            otp_correct = (otp_from_user_input == otp_string)
        else:
            otp_correct = True
            
        if otp_correct:
            box_key = get_nacl_box_key_from_file_func(box_key_file_path)
            box = nacl.secret.SecretBox(box_key)
            pastel_id_public_key_b16_encoded = pastel_id_public_key_export_format.replace("-----BEGIN ED521 PUBLIC KEY-----\n","").replace("\n-----END ED521 PUBLIC KEY-----","")
            pastel_id_private_key_export_format = box.decrypt(pastel_id_private_key_export_format__encrypted)
            pastel_id_private_key_export_format = pastel_id_private_key_export_format.decode('utf-8')
            pastel_id_private_key_b16_encoded = pastel_id_private_key_export_format.replace("-----BEGIN ED521 PRIVATE KEY-----\n","").replace("\n-----END ED521 PRIVATE KEY-----","")
    else:
        pastel_id_public_key_b16_encoded = ''
        pastel_id_private_key_b16_encoded = ''
    return pastel_id_public_key_b16_encoded, pastel_id_private_key_b16_encoded

def generate_qr_codes_from_pastel_keypair_func(pastel_id_public_key_b16_encoded, pastel_id_private_key_b16_encoded):
    qr_error_correcting_level = 'M' # L, M, Q, H
    qr_encoding_type = 'alphanumeric'
    qr_scale_factor = 6
    pastel_id_public_key_b16_encoded_qr_code = pyqrcode.create(pastel_id_public_key_b16_encoded, error=qr_error_correcting_level, version=16, mode=qr_encoding_type)
    pastel_id_private_key_b16_encoded_qr_code = pyqrcode.create(pastel_id_private_key_b16_encoded, error=qr_error_correcting_level, version=31, mode=qr_encoding_type)
    pastel_id_keys_storage_folder_path = os.getcwd() + os.sep + 'pastel_id_key_files' + os.sep
    if not os.path.isdir(pastel_id_keys_storage_folder_path):
        try:
            os.makedirs(pastel_id_keys_storage_folder_path)
        except:
            print('Error creating directory-- instead saving to current working directory!')
            pastel_id_keys_storage_folder_path = os.getcwd() + os.sep
    pastel_id_public_key_b16_encoded_qr_code.png(file=pastel_id_keys_storage_folder_path + 'pastel_id_ed521_public_key_qr_code.png', scale=qr_scale_factor)
    pastel_id_private_key_b16_encoded_qr_code.png(file=pastel_id_keys_storage_folder_path + 'pastel_id_ed521_private_key_qr_code.png',scale=qr_scale_factor)

def break_string_into_chunks_func(input_string, chunk_length, padvalue=None):
    list_of_string_chunks = [input_string[ii:ii+chunk_length] for ii in range(0, len(input_string), chunk_length)]
    return list_of_string_chunks

def generate_signature_image_layer_func(pastel_id_public_key_b16_encoded, pastel_id_signature_b16_encoded, sample_image_file_path):
    qr_error_correcting_level = 'M' # L, M, Q, H
    qr_encoding_type = 'alphanumeric'
    qr_scale_factor = 4
    max_chunk_length_for_qr_code = 150
    scale_reduction_factor = 0.80
    pastel_id_signature_b16_encoded__list_of_chunks = break_string_into_chunks_func(pastel_id_signature_b16_encoded, max_chunk_length_for_qr_code)
    pastel_id_public_key_b16_encoded_qr_code = pyqrcode.create(pastel_id_public_key_b16_encoded, error=qr_error_correcting_level, version=16, mode=qr_encoding_type)
    list_of_pastel_id_signature_b16_encoded_qr_code = [pyqrcode.create(x, error=qr_error_correcting_level, version=31, mode=qr_encoding_type) for x in pastel_id_signature_b16_encoded__list_of_chunks]
    number_of_signature_qr_codes = len(list_of_pastel_id_signature_b16_encoded_qr_code)
    pastel_id_signatures_storage_folder_path = os.getcwd() + os.sep + 'pastel_id_signature_files' + os.sep
    current_datetime_string = datetime.now().strftime("%b_%d_%Y__%H_%M_%S")
    if not os.path.isdir(pastel_id_signatures_storage_folder_path):
        try:
            os.makedirs(pastel_id_signatures_storage_folder_path)
        except:
            print('Error creating directory-- instead saving to current working directory!')
            pastel_id_signatures_storage_folder_path = os.getcwd() + os.sep
    pastel_id_public_key_b16_encoded_qr_code.png(file=pastel_id_signatures_storage_folder_path + 'pastel_id_ed521_public_key_qr_code' + current_datetime_string + '.png', scale=qr_scale_factor)
    for idx, current_signature_qr_code in enumerate(list_of_pastel_id_signature_b16_encoded_qr_code):
        current_signature_qr_code.png(file=pastel_id_signatures_storage_folder_path + 'pastel_id_ed521_signature_qr_code__part_'+ str(idx) + '_of_' + str(number_of_signature_qr_codes) + current_datetime_string + '.png', scale=qr_scale_factor)
    list_of_qr_code_file_paths =  glob.glob(pastel_id_signatures_storage_folder_path + os.sep + '*' + current_datetime_string + '*')
    sample_image_pil = Image.open(sample_image_file_path)
    output_image_width, output_image_height = sample_image_pil.size #getting the base image's size
    list_of_qr_code_image_widths = [Image.open(x).size[0] for x in list_of_qr_code_file_paths]
    list_of_qr_code_image_heights = [Image.open(x).size[1] for x in list_of_qr_code_file_paths]
    sum_of_widths_plus_borders = sum(list_of_qr_code_image_widths) + 3*(len(list_of_qr_code_image_widths) - 1)
    max_height_of_qr_codes = max(list_of_qr_code_image_heights)
    assert(max_height_of_qr_codes <= output_image_height)
    if output_image_width < sum_of_widths_plus_borders:
        width_resize_ratio = sum_of_widths_plus_borders/output_image_width
        print('All QR code images widths together are larger than the destination image width-- scaling by factor of ' + str(round(1/width_resize_ratio,7)))
        list_of_qr_code_image_widths__resized = [math.floor(scale_reduction_factor*x/width_resize_ratio) for x in list_of_qr_code_image_widths]
        list_of_qr_code_image_heights__resized = [math.floor(scale_reduction_factor*x/width_resize_ratio) for x in list_of_qr_code_image_heights]
        list_of_qr_code_images = [Image.open(x) for x in list_of_qr_code_file_paths]
        list_of_qr_code_images__resized = []
        for idx, current_qr_code_image in enumerate(list_of_qr_code_images):
            resized_qr_code_image = current_qr_code_image.resize((list_of_qr_code_image_widths__resized[idx], list_of_qr_code_image_heights__resized[idx]), Image.ANTIALIAS)
            list_of_qr_code_images__resized = list_of_qr_code_images__resized + [resized_qr_code_image]
    else:
        list_of_qr_code_image_widths__resized = list_of_qr_code_image_widths
        list_of_qr_code_image_heights__resized = list_of_qr_code_image_heights
        list_of_qr_code_images__resized = [Image.open(x) for x in list_of_qr_code_file_paths]
    signature_layer_image = Image.new('RGB', (output_image_width, output_image_height))
    padding_pixels = 2
    for indx, current_qr_code_image in enumerate(list_of_qr_code_images__resized):
        if indx==0:
            current_qr_image_x_coordinate = 0
            caption_text = 'Pastel Public Key'
            caption_x_position = round(list_of_qr_code_image_widths__resized[indx]/2, 0)
        else:
            current_qr_image_x_coordinate = current_qr_image_x_coordinate + list_of_qr_code_image_widths__resized[indx-1] + padding_pixels
            caption_text = 'Pastel Signature Part ' + str(indx)  + ' of ' + str(len(list_of_qr_code_images__resized)-1)
            caption_x_position = round(list_of_qr_code_image_widths__resized[indx-1]/2, 0)
        drawing_context = ImageDraw.Draw(current_qr_code_image)
        font1 = ImageFont.truetype('arial.ttf', 12)
        drawing_context.text((caption_x_position, 0), caption_text, font=font1) 
        signature_layer_image.paste(current_qr_code_image, (current_qr_image_x_coordinate, 0))
    #signature_layer_image.show()
    signature_layer_image_output_filepath = pastel_id_signatures_storage_folder_path + "Complete_Signature_Image_Layer__" + current_datetime_string + ".png"
    signature_layer_image.save(signature_layer_image_output_filepath, "PNG")
    return signature_layer_image, signature_layer_image_output_filepath

def get_sha256_hash_of_input_data_func(input_data_or_string):
    if isinstance(input_data_or_string, str):
        input_data_or_string = input_data_or_string.encode('utf-8')
    sha256_hash_of_input_data = hashlib.sha3_256(input_data_or_string).hexdigest()
    return sha256_hash_of_input_data

def get_image_hash_from_image_file_path_func(path_to_art_image_file):
    try:
        with open(path_to_art_image_file,'rb') as f:
            art_image_file_binary_data = f.read()
        sha256_hash_of_art_image_file = get_sha256_hash_of_input_data_func(art_image_file_binary_data)
        return sha256_hash_of_art_image_file
    except Exception as e:
        print('Error: '+ str(e))

class Steganography:
    def embed(self, cover_file, secret_file, color_plane, pixel_bit):
        cover_array = self.image_to_matrix(cover_file)
        secret_array = self.image_to_matrix(secret_file)
        # every bit except the one at `pixel_bit` position is 1
        mask = 0xff ^ (1 << pixel_bit)
        # shift the MSB of the secret to the `pixel_bit` position
        secret_bits = ((secret_array[...,color_plane] >> 7) << pixel_bit)
        height, width, _ = secret_array.shape
        cover_plane = (cover_array[:height,:width,color_plane] & mask) + secret_bits
        cover_array[:height,:width,color_plane] = cover_plane
        stego_image = self.matrix_to_image(cover_array)
        return stego_image

    def extract(self, stego_file, color_plane, pixel_bit):
        stego_array = self.image_to_matrix(stego_file)
        change_index = [0, 1, 2]
        change_index.remove(color_plane)
        stego_array[...,change_index] = 0
        stego_array = ((stego_array >> pixel_bit) & 0x01) << 7
        exposed_secret = self.matrix_to_image(stego_array)
        return exposed_secret

    def image_to_matrix(self, file_path):
        return np.array(Image.open(file_path))

    def matrix_to_image(self, array):
        return Image.fromarray(array)

def hide_signature_image_in_sample_image_func(sample_image_file_path, signature_layer_image_output_filepath, signed_image_output_path):
    S = Steganography()
    plane = 0
    bit = 1
    S.embed(sample_image_file_path, signature_layer_image_output_filepath, plane, bit).save(signed_image_output_path)

def extract_signature_image_in_sample_image_func(signed_image_output_path, extracted_signature_layer_image_output_filepath):
    S = Steganography()
    plane = 0
    bit = 1
    S.extract(signed_image_output_path, plane, bit).save(extracted_signature_layer_image_output_filepath)


#Settings: 
use_demonstrate_eddsa_crypto = 1
use_demonstrate_signature_qr_code_steganography = 1

generate_google_auth_qr_code = input('\n\nHave you already generated a Google Authenticator QR code for Pastel? (Y or N):\n')
if generate_google_auth_qr_code == "N" or generate_google_auth_qr_code == "n":
    google_auth_secret = set_up_google_authenticator_for_private_key_encryption_func()
generate_and_store_key_for_nacl_box_func()
box_key_file_path = 'box_key.bin'
sample_image_file_path = 'sample_image2.png'

if use_demonstrate_eddsa_crypto:
    print('\nApplying signature to file: ' + sample_image_file_path)
    sha256_hash_of_image_to_sign = get_image_hash_from_image_file_path_func(sample_image_file_path)
    print('\nSHA256 Hash of Image File: ' + sha256_hash_of_image_to_sign)
    sample_input_data_to_be_signed = sha256_hash_of_image_to_sign.encode('utf-8')
    use_require_otp = 1
    pastel_id_public_key_b16_encoded, pastel_id_private_key_b16_encoded = import_pastel_public_and_private_keys_from_pem_files_func(use_require_otp, box_key_file_path)
    if pastel_id_public_key_b16_encoded == '':
        pastel_id_private_key_b16_encoded, pastel_id_public_key_b16_encoded = pastel_id_keypair_generation_func()
        write_pastel_public_and_private_key_to_file_func(pastel_id_public_key_b16_encoded, pastel_id_private_key_b16_encoded, box_key_file_path)
        generate_qr_codes_from_pastel_keypair_func(pastel_id_public_key_b16_encoded, pastel_id_private_key_b16_encoded)
    pastel_id_signature_b16_encoded = pastel_id_write_signature_on_data_func(sample_input_data_to_be_signed, pastel_id_private_key_b16_encoded, pastel_id_public_key_b16_encoded)
    verified = pastel_id_verify_signature_with_public_key_func(sample_input_data_to_be_signed, pastel_id_signature_b16_encoded, pastel_id_public_key_b16_encoded)

if use_demonstrate_signature_qr_code_steganography:
    signature_layer_image_pil, signature_layer_image_output_filepath = generate_signature_image_layer_func(pastel_id_public_key_b16_encoded, pastel_id_signature_b16_encoded, sample_image_file_path)    
    signed_image_output_path = 'final_watermarked_image.png'
    hide_signature_image_in_sample_image_func(sample_image_file_path, signature_layer_image_output_filepath, signed_image_output_path)
    
    extracted_signature_layer_image_output_filepath = 'extracted_signature_image.png'
    extract_signature_image_in_sample_image_func(signed_image_output_path, extracted_signature_layer_image_output_filepath)