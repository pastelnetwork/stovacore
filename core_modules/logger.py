import logging

loggers = {}


def initlogging(logger_name, module, level="error"):
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
        consolehandler = logging.StreamHandler()
        consolehandler.setFormatter(formatter)
        logger.addHandler(consolehandler)

        # record this logger
        loggers[name] = logger

    return logger
