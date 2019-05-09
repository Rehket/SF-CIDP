
from typing import List
from loguru import logger
from pathlib import Path
import subprocess
from os import environ


def execute(cmd: List[str], cwd: str):
    """
    Execute commands in a shell and pipe them to stdout
    :param cmd: Commands to run in a list of strings
    :param cwd: the working directory to execute the commands in.
    :return:
    """
    logger.info(f"Executing {cmd} in shell.")
    popen = subprocess.Popen(
        cmd,
        cwd=Path(environ.get("WORKING_DIR", "working_dir"), cwd),
        stdout=subprocess.PIPE,
        universal_newlines=True,
        shell=True,
    )
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line.strip("\n")
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

