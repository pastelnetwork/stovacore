from core_modules.logger import initlogging


class ClientNodeManager:
    def __init__(self):
        self.__logger = initlogging('ClientNodeManager', __name__)
