from argparse import ArgumentParser
import json
import sys


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


def get_dependency_targets(images_data, target, action):
    action_targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: action in x["actions"], images_data)
    ]
    target_dependencies = set()
    image_config = get_image_config(images_data, target)
    if image_config.get("dependencies"):
        target_dependencies.update(set([(dep["name"], dep["tag"]) for dep in image_config["dependencies"]]))

    return_deps = target_dependencies.intersection(action_targets)
    for dep in return_deps.copy():
        return_deps.update(get_dependency_targets(images_data, dep, action))
    return return_deps


def pull_images(images_data, targets=[]):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "pull" in x["actions"], images_data)
        ]
    pull_targets = set(targets)
    for target in pull_targets:
        image = get_image_config(images_data, target)
        print(f"Pulling image {image['name']}:{image['tag']} with the following config: {image}")


def build_images(images_data, targets=[]):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "build" in x["actions"], images_data)
        ]
    build_targets = set(targets)
    for target in build_targets.copy():
        build_targets.update(get_dependency_targets(images_data, target, "build"))
    for target in build_targets:
        image = get_image_config(images_data, target)
        print(f"Building image {image['name']}:{image['tag']} with the following config: {image}")


def validate_images_schema(images):
    if not isinstance(images, list):
        raise ValueError("Base object is not a list")
    for image in images:
        # First check required fields
        if "name" not in image:
            raise ValueError("Missing field in image: name")
        elif not isinstance(image["name"], str):
            raise ValueError("Incorrect field type in image: name must be type string")
        if "tag" not in image:
            raise ValueError("Missing field in image: tag")
        elif not isinstance(image["tag"], str):
            raise ValueError("Incorrect field type in image: tag must be type string")
        if "actions" not in image:
            raise ValueError("Missing field in image: actions")
        elif not isinstance(image["actions"], list):
            raise ValueError("Incorrect field type in image: actions must be type list")
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
            raise ValueError("Incorrect field type in image: target must be type str")
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
        image["name"] for image in filter(lambda x: "pull" in x["actions"], images)
    ]
    for image in images:
        if "dependencies" in image:
            for dependency in image["dependencies"]:
                if dependency["name"] not in image_names:
                    raise ValueError(
                        f"Image {image['name']} has a dependency on {dependency['name']} which does not exist"
                    )
    # TODO check for circular dependencies


def main():
    parser = ArgumentParser("wake")
    parser.add_argument("--config", type=str, default="wake.json")
    parser.add_argument("--tag-prefix", type=str, default="")
    parser.add_argument("--cosign-profile", type=str, default=None)
    subparsers = parser.add_subparsers(dest="action", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.set_defaults(func=build_images)
    build_parser.add_argument("targets", nargs="*", default=[])
    pull_parser = subparsers.add_parser("pull")
    pull_parser.set_defaults(func=pull_images)
    pull_parser.add_argument("targets", type=str, nargs="*")
    args = parser.parse_args()
    with open(args.config, "r") as f:
        images_data = json.load(f)
    try:
        validate_images_schema(images_data)
        validate_images_dependencies(images_data)
        targets = get_matching_targets(images_data, args.targets, args.action)
    except ValueError as e:
        exit(f"Invalid images file: {e}")
    return args.func(images_data, targets)


if __name__ == "__main__":
    sys.exit(main())
