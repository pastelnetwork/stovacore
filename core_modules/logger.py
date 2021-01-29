import logging
import logging.handlers
import os

from core_modules.settings import Settings, LOG_DESTINATION_STDOUT

loggers = {}


def get_logger(name, level=Settings.LOG_LEVEL):
    logger = loggers.get(name)
    if logger is None:
        logger = logging.getLogger(name)

        if level == "debug":
            logger.setLevel(logging.DEBUG)
        elif level == "info":
            logger.setLevel(logging.INFO)
        elif level == "warning":
            logger.setLevel(logging.WARNING)
        elif level == "error":
            logger.setLevel(logging.ERROR)
        elif level == "critical":
            logger.setLevel(logging.CRITICAL)
        else:
            raise ValueError("Invalid level: %s" % level)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:' + name + ': - %(message)s')

        # use file handler for pyNode and console handler for wallet
        if os.environ.get('PYNODE_MODE') == 'WALLET' or Settings.LOG_DESTINATION == LOG_DESTINATION_STDOUT:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        else:
            # total maximum 5 files up to 100MB each
            file_handler = logging.handlers.RotatingFileHandler(Settings.LOG_DESTINATION, maxBytes=100 * 1024 * 1024, backupCount=5)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # record this logger
        loggers[name] = logger
        # logger.debug("%s Logger started" % name)
    return logger
