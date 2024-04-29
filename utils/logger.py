import logging
import sys
from asyncio.log import logger

def create_logger():
    formatter = logging.Formatter(
            "[%(asctime)s] %(filename)s:%(lineno)d / %(funcName)s %(levelname)s - %(message)s"
        )

    handler = logging.StreamHandler(sys.stdout)


    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logging.getLogger()