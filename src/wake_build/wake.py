import json
import os
import subprocess
import sys
from argparse import ArgumentParser


def build_image(config, dry_run=False) -> bool:
    build_args = [
        "docker",
        "build",
        "--tag",
        f"{config['name']}:{config['tag']}",
    ]
    if "target" in config:
        build_args.extend(["--target", config["target"]])
    if "dockerfile" in config:
        build_args.extend(["--file", config["dockerfile"]])
    if "build_args" in config:
        for key, value in config["build_args"].items():
            build_args.extend(["--build-arg", f"{key}={value}"])
    if "env_args" in config:
        for key in config["env_args"]:
            build_args.extend(
                ["--build-arg", f"{key}={os.environ.get(key, '')}"]
            )
    if "context" in config:
        build_args.append(config["context"])
    else:
        build_args.append(".")
    if not dry_run:
        proc = subprocess.run(build_args)
        return proc.returncode == 0
    else:
        print(" ".join(build_args))
        return True


def pull_image(config, dry_run=False) -> bool:
    cmd = ["docker", "pull", f"{config['name']}:{config['tag']}"]
    if not dry_run:
        proc = subprocess.run(cmd)
        return proc.returncode == 0
    else:
        print(" ".join(cmd))
        return True


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
    if not dry_run:
        proc = subprocess.run(cmd)
        return proc.returncode == 0
    else:
        print(" ".join(cmd))
        return True


def push_image(config, prefix="", dry_run=False) -> bool:
    cmd = ["docker", "push", f"{prefix}{config['name']}:{config['tag']}"]
    if not dry_run:
        proc = subprocess.run(cmd)
        return proc.returncode == 0
    else:
        print(" ".join(cmd))
        return True


def get_image_config(images_config, name_tag: tuple):
    name, tag = name_tag
    for image in images_config:
        if image["name"] == name and image["tag"] == tag:
            return image
    return None


def get_matching_targets(images_data, targets, action):
    matches = []
    for target in targets:
        found = False
        split = target.split(":")
        if len(split) == 1:
            for image in filter(lambda x: action in x["actions"], images_data):
                if image["name"] == split[0]:
                    found = True
                    matches.append((image["name"], image["tag"]))
        elif len(split) == 2:
            for image in filter(lambda x: action in x["actions"], images_data):
                if image["name"] == split[0] and image["tag"] == split[1]:
                    found = True
                    matches.append((image["name"], image["tag"]))
        else:
            raise ValueError(f"Invalid target format: {target}")
        if not found:
            raise ValueError(f"Target {target} not found for action {action}")
    return matches


def get_dependency_targets(images_data, target, action) -> set:
    action_targets = [
        (image["name"], image["tag"])
        for image in filter(lambda x: action in x["actions"], images_data)
    ]
    target_dependencies = set()
    image_config = get_image_config(images_data, target)
    if image_config.get("dependencies"):
        target_dependencies.update(
            set(
                [
                    (dep["name"], dep["tag"])
                    for dep in image_config["dependencies"]
                ]
            )
        )

    return_deps = target_dependencies.intersection(action_targets)
    for dep in return_deps.copy():
        return_deps.update(get_dependency_targets(images_data, dep, action))
    return return_deps


def pull_images(images_data, targets=[], dry_run=False, **_):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "pull" in x["actions"], images_data)
        ]
    pull_targets = set(targets)
    for target in pull_targets:
        image = get_image_config(images_data, target)
        success = pull_image(image, dry_run=dry_run)
        if not success:
            exit(f"Failed to pull image: {image['name']}:{image['tag']}")


def build_images(images_data, targets=[], dry_run=False, **_):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "build" in x["actions"], images_data)
        ]
    build_targets = set(targets)
    for target in build_targets.copy():
        dep_targets = get_dependency_targets(images_data, target, "build")
        build_targets.update(dep_targets)
    remaining_targets = build_targets.copy()
    while len(remaining_targets):
        did_something = False
        for target in remaining_targets.copy():
            image = get_image_config(images_data, target)
            for dep in image.get("dependencies", []):
                # Will only be in remaining_targets if it requires building
                if (dep["name"], dep["tag"]) in remaining_targets:
                    break
            # TODO add a way to build images concurrently when possible
            if not build_image(image, dry_run=dry_run):
                exit(f"Failed to build image: {image['name']}:{image['tag']}")
            remaining_targets.remove(target)
            did_something = True
        if not did_something:
            raise ValueError("Circular dependency detected")


def tag_images(images_data, targets=[], prefix="", dry_run=False, **_):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "tag" in x["actions"], images_data)
        ]
    tag_targets = set(targets)
    for target in tag_targets:
        image = get_image_config(images_data, target)
        success = tag_image(image, prefix=prefix, dry_run=dry_run)
        if not success:
            exit(f"Failed to tag image: {image['name']}:{image['tag']}")


def push_images(images_data, targets=[], prefix="", dry_run=False, **_):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "push" in x["actions"], images_data)
        ]
    push_targets = set(targets)
    for target in push_targets:
        image = get_image_config(images_data, target)
        success = push_image(image, prefix=prefix, dry_run=dry_run)
        if not success:
            exit(f"Failed to push image: {image['name']}:{image['tag']}")


def validate_images_schema(images):
    if not isinstance(images, list):
        raise ValueError("Base object is not a list")
    for image in images:
        # First check required fields
        if "name" not in image:
            raise ValueError("Missing field in image: name")
        elif not isinstance(image["name"], str):
            raise ValueError(
                "Incorrect field type in image: name must be type string"
            )
        if "tag" not in image:
            raise ValueError("Missing field in image: tag")
        elif not isinstance(image["tag"], str):
            raise ValueError(
                "Incorrect field type in image: tag must be type string"
            )
        if "actions" not in image:
            raise ValueError("Missing field in image: actions")
        elif not isinstance(image["actions"], list):
            raise ValueError(
                "Incorrect field type in image: actions must be type list"
            )
        else:
            for action in image["actions"]:
                if not isinstance(action, str):
                    raise ValueError(
                        "Incorrect field type in image: action must be type string"
                    )
                if action not in ["pull", "build", "tag", "push", "sign"]:
                    raise ValueError(
                        "Incorrect field value in image: action must be one of 'pull', 'build', 'tag', 'push', 'sign'"
                    )
        # Next check optional fields
        if "target" in image and not isinstance(image["target"], str):
            raise ValueError(
                "Incorrect field type in image: target must be type str"
            )
        if "dockerfile" in image and not isinstance(image["dockerfile"], str):
            raise ValueError(
                "Incorrect field type in image: dockerfile must be type str"
            )
        if "dependencies" in image:
            if not isinstance(image["dependencies"], list):
                raise ValueError(
                    "Incorrect field type in image: dependencies must be type list"
                )
            # Check dependency format
            for dependency in image["dependencies"]:
                # First check required fields
                if "name" not in dependency:
                    raise ValueError("Missing field in dependency: name")
                elif not isinstance(dependency["name"], str):
                    raise ValueError(
                        "Incorrect field type in dependency: name must be type string"
                    )
                if "tag" not in dependency:
                    raise ValueError("Missing field in dependency: tag")
                elif not isinstance(dependency["tag"], str):
                    raise ValueError(
                        "Incorrect field type in dependency: tag must be type string"
                    )


def validate_images_dependencies(images):
    # Check that all dependencies are defined
    image_names = [image["name"] for image in images]
    image_names = [
        image["name"]
        for image in filter(
            lambda x: len({"pull", "build"}.intersection(set(x["actions"]))),
            images,
        )
    ]
    for image in images:
        if "dependencies" in image:
            for dependency in image["dependencies"]:
                if dependency["name"] not in image_names:
                    raise ValueError(
                        f"Image {image['name']} has a dependency on {dependency['name']} which does not exist or has no pull or build action"
                    )
    # TODO check for circular dependencies


def main():
    parser = ArgumentParser("wake")
    parser.add_argument("-f", "--config", type=str, default="Wakefile")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-d", "--default-tag", type=str, default="latest")
    parser.add_argument("-t", "--tag-prefix", type=str, default=None)
    parser.add_argument("-p", "--cosign-profile", type=str, default=None)
    subparsers = parser.add_subparsers(dest="action", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.set_defaults(func=build_images)
    build_parser.add_argument("targets", nargs="*", default=[])

    pull_parser = subparsers.add_parser("pull")
    pull_parser.set_defaults(func=pull_images)
    pull_parser.add_argument("targets", type=str, nargs="*")

    tag_parser = subparsers.add_parser("tag")
    tag_parser.set_defaults(func=tag_images)
    tag_parser.add_argument("targets", type=str, nargs="*")

    push_parser = subparsers.add_parser("push")
    push_parser.set_defaults(func=push_images)
    push_parser.add_argument("targets", type=str, nargs="*")

    args = parser.parse_args()
    try:
        with open(args.config, "r") as f:
            images_data = json.load(f)
    except FileNotFoundError:
        exit(f"Could not find config file: {args.config}")
    # Set default tags
    for image in images_data:
        if "tag" not in image:
            image["tag"] = args.default_tag
    try:
        validate_images_schema(images_data)
        validate_images_dependencies(images_data)
        targets = get_matching_targets(images_data, args.targets, args.action)
    except ValueError as e:
        exit(f"Invalid images file: {e}")
    prefix = (
        args.tag_prefix
        if args.tag_prefix is not None
        else os.environ.get("TAG_PREFIX", "")
    )
    return args.func(images_data, targets, prefix=prefix)


if __name__ == "__main__":
    sys.exit(main())
