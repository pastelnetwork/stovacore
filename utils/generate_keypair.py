import sys
import os

# PATH HACK
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from core_modules.blackbox_modules import keys


if __name__ == "__main__":
    priv, pub = keys.id_keypair_generation_func()
    print("PRIV:", priv)
    print("PUB:", pub)
