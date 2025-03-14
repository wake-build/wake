from wake_build.util import run_command
import os


def build_image(config, dry_run=False) -> bool:
    cmd = [
        "docker",
        "build",
        "--tag",
        f"{config['name']}:{config['tag']}",
    ]
    if "target" in config:
        cmd.extend(["--target", config["target"]])
    if "dockerfile" in config:
        cmd.extend(["--file", config["dockerfile"]])
    if "build_args" in config:
        for key, value in config["build_args"].items():
            cmd.extend(["--build-arg", f"{key}={value}"])
    if "env_args" in config:
        for key in config["env_args"]:
            cmd.extend(["--build-arg", f"{key}={os.environ.get(key, '')}"])
    if "context" in config:
        cmd.append(config["context"])
    else:
        cmd.append(".")
    return run_command(cmd, dry_run=dry_run)


def pull_image(config, dry_run=False) -> bool:
    cmd = ["docker", "pull", f"{config['name']}:{config['tag']}"]
    return run_command(cmd, dry_run=dry_run)


def tag_image(config, prefix="", dry_run=False) -> bool:
    if not prefix:
        # Skip tagging if no prefix is provided
        return True
    cmd = [
        "docker",
        "tag",
        f"{config['name']}:{config['tag']}",
        f"{prefix}{config['name']}:{config['tag']}",
    ]
    return run_command(cmd, dry_run=dry_run)


def push_image(config, prefix="", dry_run=False) -> bool:
    cmd = ["docker", "push", f"{prefix}{config['name']}:{config['tag']}"]
    return run_command(cmd, dry_run=dry_run)
