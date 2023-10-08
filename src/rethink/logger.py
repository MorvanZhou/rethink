import logging

# import os
# from logging.handlers import RotatingFileHandler

# disable 3rd party log
logging.basicConfig(
    level=logging.ERROR,
    format="%(levelname)s | %(asctime)s | %(name)s | %(filename)s[line:%(lineno)d]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("root")
logger.setLevel(logging.INFO)
