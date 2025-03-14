import os
import json
import yaml

from wake_build.exc import NoConfigFoundException


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


def load_json(path):
    try:
        with open(path, "r") as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error loading JSON file: {e}")


def load_yaml(path):
    try:
        try:
            with open(path, "r") as file:
                return yaml.safe_load(file)
        except yaml.composer.ComposerError:
            with open(path, "r") as file:
                return list(yaml.safe_load_all(file))
    except yaml.YAMLError as e:
        raise ValueError(f"Error loading YAML file: {e}")


def load_config(location):
    configs = []
    try:
        if os.path.isdir(location):
            for filename in os.listdir(location):
                for load_method in [load_json, load_yaml]:
                    try:
                        data = load_method(os.path.join(location, filename))
                        if isinstance(data, dict):
                            configs.append(data)
                        elif isinstance(data, list):
                            configs.extend(data)
                        break
                    except ValueError:
                        continue
        else:
            for load_method in [load_json, load_yaml]:
                try:
                    data = load_method(location)
                    if isinstance(data, dict):
                        configs.append(data)
                    elif isinstance(data, list):
                        configs.extend(data)
                    break
                except ValueError:
                    continue
        return configs
    except FileNotFoundError:
        raise NoConfigFoundException(location)


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
