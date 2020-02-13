import logging
import os
import locale  # To convert numbers into Currency

def init_logger(log_file):
    logfile = os.path.abspath(log_file)
    log = logging.getLogger(logfile)
    handler = logging.handlers.RotatingFileHandler(logfile, maxBytes=20971520, backupCount=50)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)

    return log


def get_currency_format(value, currency_format='en_IN'):
    locale.setlocale(locale.LC_ALL, currency_format)
    return locale.currency(value, grouping=True)
