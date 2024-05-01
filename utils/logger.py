import logging
import sys
from asyncio.log import logger

def create_logger():

    log_format = "[%(asctime)s] %(filename)s:%(lineno)d / %(funcName)s %(levelname)s - %(message)s"
    logging.basicConfig(format=log_format, level=logging.INFO)
    logger_to_return = logging.getLogger()
    return logger_to_return