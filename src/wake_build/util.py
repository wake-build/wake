import sys
import subprocess

from wake_build.log import logger


def run_command(command, dry_run=False):
    logger.info(f"Running command: `{' '.join(command)}`")
    if dry_run:
        return True
    proc = subprocess.run(command, capture_output=True)
    if proc.returncode:
        logger.error(
            f"Command `{' '.join(command)}` failed with return code: {proc.returncode}"
        )
        sys.stdout.write(proc.stderr.decode())
    return proc.returncode == 0
