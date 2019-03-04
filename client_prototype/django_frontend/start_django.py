#!/usr/bin/env python
import os
import sys

from django.core.management import execute_from_command_line

# add project root before importing project modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../../../python_layer/")

from core_modules.settings import NetWorkSettings

if __name__ == '__main__':
    print("Starting django pid %s with parameters: %s" % (os.getpid(), sys.argv))

    # add project root and django root folder to path
    sys.path.append(NetWorkSettings.DJANGO_ROOT)

    # parse arguments
    argv0, http_port, pastel_basedir, patel_rpc_ip, pastel_rpc_port, pastel_rpc_pubkey = sys.argv

    os.environ["PASTEL_BASEDIR"] = pastel_basedir
    os.environ["PASTEL_RPC_IP"] = patel_rpc_ip
    os.environ["PASTEL_RPC_PORT"] = pastel_rpc_port
    os.environ["PASTEL_RPC_PUBKEY"] = pastel_rpc_pubkey

    # vvvvv this code is from the original manage.py vvvvv
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'frontend.settings')

    # we modify the function call to run the server
    execute_from_command_line([argv0, "runserver", http_port, "--noreload"])
