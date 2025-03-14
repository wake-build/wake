import logging

logger = logging.getLogger("wake")


# Custom log formatter class
class LogFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    green = "\x1b[33;92m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(levelname)s: %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
        logging.FATAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def configure_logger(verbosity_count):
    log_level = logging.WARNING
    if verbosity_count >= 2:
        log_level = logging.DEBUG
        show_progress = False
    elif verbosity_count == 1:
        log_level = logging.INFO
        show_progress = False
    elif verbosity_count == 0:
        log_level = logging.WARNING
    elif verbosity_count < 0:
        log_level = logging.ERROR
    logger.setLevel(log_level)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(LogFormatter())
    logger.addHandler(ch)
