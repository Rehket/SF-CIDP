import subprocess

import shutil
import os
import sys
import json
from pathlib import Path
from typing import List
from prefect import task as prefect_task
from loguru import logger

import config

logger.add(sys.stdout, format="{time} {level} {message}", level="DEBUG")


if __name__ == "__main__":
    pass
