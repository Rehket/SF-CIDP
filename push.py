
import sys
from loguru import logger

logger.add(sys.stdout, format="{time} {level} {message}", level="DEBUG")


if __name__ == "__main__":
    pass
