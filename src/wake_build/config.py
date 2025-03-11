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
