import os
from PastelCommon.keys import id_keypair_generation_func

if __name__ == '__main__':
    __privkey, __pubkey = id_keypair_generation_func()
    privpath = 'private.key'
    pubpath = 'public.key'
    with open(privpath, "wb") as f:
        f.write(__privkey)
    os.chmod(privpath, 0o0700)
    with open(pubpath, "wb") as f:
        f.write(__pubkey)
    os.chmod(pubpath, 0o0700)
