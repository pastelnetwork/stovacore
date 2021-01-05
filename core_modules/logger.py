import logging
import logging.handlers
import os

from core_modules.settings import Settings

loggers = {}

LOG_FILENAME = 'pynode.log'


def initlogging(logger_name, module, level=Settings.LOG_LEVEL):
    name = "%s - %s" % (logger_name, module)

    # TODO: perhaps this can be done in a more elegant way?
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

        formatter = logging.Formatter(' %(asctime)s - ' + name + ' - %(levelname)s - %(message)s')

        # use file handler for pyNode and console handler for wallet
        if os.environ.get('PYNODE_MODE') == 'WALLET':
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        else:
            # total maximum 5 files up to 100MB each
            file_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=100 * 1024 * 1024, backupCount=5)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # record this logger
        loggers[name] = logger

        logger.debug("%s Logger started" % logger_name)

    return logger
