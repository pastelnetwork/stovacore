import asyncio

from django.core.management.base import BaseCommand, CommandError

from core.models import logger, nodemanager


class Command(BaseCommand):
    help = 'Tests the zmq RPC connection'

    def handle(self, *args, **options):
        mn = nodemanager.get_random()
        new_loop = asyncio.new_event_loop()
        new_loop.run_until_complete(mn.send_rpc_ping(b'PING'))
        new_loop.stop()
