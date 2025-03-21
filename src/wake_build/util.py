import sys
import subprocess

from wake_build.log import logger


def run_command(command, dry_run=False, live_output=False):
    logger.info(f"Running command: `{' '.join(command)}`")
    if dry_run:
        return True
    args = {
        "stderr": None if live_output else subprocess.PIPE,
        "stdout": None if live_output else subprocess.PIPE,
    }
    proc = subprocess.run(command, **args)
    if proc.returncode:
        if not live_output:
            logger.error(
                f"Command `{' '.join(command)}` failed with return code: {proc.returncode}"
            )
        sys.stdout.write(proc.stderr.decode())
    return proc.returncode == 0
