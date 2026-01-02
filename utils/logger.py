import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(name)-12s | %(message)s",
    handlers=[
        logging.StreamHandler()
    ])

def get_logger(name):
    return logging.getLogger(name)
