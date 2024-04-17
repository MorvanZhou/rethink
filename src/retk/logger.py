import logging

import os
from logging.handlers import RotatingFileHandler

log_format = "%(levelname)s | %(asctime)s | %(name)s | %(filename)s[line:%(lineno)d]: %(message)s"
log_date_format = "%Y-%m-%d %H:%M:%S"
logging.basicConfig(
    level=logging.ERROR,
    format=log_format,
    datefmt=log_date_format,
)
logger = logging.getLogger("rethink")
logger.setLevel(logging.ERROR)


# add rotating file handler
def add_rotating_file_handler(log_dir: str, max_bytes: int, backup_count: int):
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "rethink.log"),
        encoding="utf-8",
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter(log_format, datefmt=log_date_format)
    )
    logger.addHandler(file_handler)
