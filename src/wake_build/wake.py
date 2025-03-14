import os
import subprocess
import sys
from argparse import ArgumentParser

import tqdm

from wake_build.config import (
    load_config,
    validate_images_schema,
    get_image_config,
    get_dependency_targets,
    get_matching_targets,
    validate_images_dependencies,
)
from wake_build.exc import NoConfigFoundException
from wake_build.log import logger, configure_logger
from wake_build.docker import build_image, pull_image, tag_image, push_image


def pull_images(
    images_data, targets=[], dry_run=False, show_progress=False, **_
):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "pull" in x["actions"], images_data)
        ]
    pull_targets = set(targets)
    if show_progress:
        progress = tqdm.tqdm(total=len(pull_targets), desc="Pulling")
    for target in pull_targets:
        image = get_image_config(images_data, target)
        success = pull_image(image, dry_run=dry_run)
        if not success:
            logger.critical(
                f"Failed to pull image: {image['name']}:{image['tag']}"
            )
            exit(1)
        if show_progress:
            progress.update(1)
    if show_progress:
        progress.close()


def build_images(
    images_data, targets=[], dry_run=False, show_progress=False, **_
):
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
    if show_progress:
        progress = tqdm.tqdm(total=len(remaining_targets), desc="Building")
    while len(remaining_targets):
        did_something = False
        for target in remaining_targets.copy():
            image = get_image_config(images_data, target)
            unbuilt_dependencies = False
            for dep in image.get("dependencies", []):
                # Will only be in remaining_targets if it requires building
                if (dep["name"], dep["tag"]) in remaining_targets:
                    unbuilt_dependencies = True
                    break
            if unbuilt_dependencies:
                continue
            # TODO add a way to build images concurrently when possible
            if not build_image(image, dry_run=dry_run):
                logger.critical(
                    f"Failed to build image: {image['name']}:{image['tag']}"
                )
                exit(1)
            remaining_targets.remove(target)
            did_something = True
            if show_progress:
                progress.update(1)
        if not did_something:
            raise ValueError("Circular dependency detected")
    if show_progress:
        progress.close()


def tag_images(
    images_data, targets=[], prefix="", dry_run=False, show_progress=False, **_
):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "tag" in x["actions"], images_data)
        ]
    tag_targets = set(targets)
    if show_progress:
        progress = tqdm.tqdm(total=len(tag_targets), desc="Tagging")
    for target in tag_targets:
        image = get_image_config(images_data, target)
        success = tag_image(image, prefix=prefix, dry_run=dry_run)
        if not success:
            logger.critical(
                f"Failed to tag image: {image['name']}:{image['tag']}"
            )
            exit(1)
        if show_progress:
            progress.update(1)
    if show_progress:
        progress.close()


def push_images(
    images_data, targets=[], prefix="", dry_run=False, show_progress=False, **_
):
    if not len(targets):
        targets = [
            (image["name"], image["tag"])
            for image in filter(lambda x: "push" in x["actions"], images_data)
        ]
    push_targets = set(targets)
    if show_progress:
        progress = tqdm.tqdm(total=len(push_targets), desc="Pushing")
    for target in push_targets:
        image = get_image_config(images_data, target)
        success = push_image(image, prefix=prefix, dry_run=dry_run)
        if not success:
            logger.critical(
                f"Failed to push image: {image['name']}:{image['tag']}"
            )
            exit(1)
        if show_progress:
            progress.update(1)
    if show_progress:
        progress.close()


def main():
    parser = ArgumentParser("wake")
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("-f", "--config", type=str)
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

    configure_logger(args.verbose)
    show_progress = args.verbose < 1
    images_data = []
    loaded_config = False
    if args.config:
        try:
            images_data = load_config(args.config)
            loaded_config = True
        except NoConfigFoundException:
            logger.critical(
                f"Specified config location not found: {args.config}"
            )
            exit(1)
    else:
        for location in ["Wakefile", ".wake"]:
            try:
                images_data = load_config(location)
                loaded_config = True
                break
            except NoConfigFoundException:
                pass
    if not loaded_config:
        logger.critical("No config found")
        exit(1)

    # Remove any empty images
    images_data = list(filter(lambda x: x, images_data))

    for image in images_data:
        if "tag" not in image:
            image["tag"] = args.default_tag
    try:
        validate_images_schema(images_data)
        validate_images_dependencies(images_data)
        targets = get_matching_targets(images_data, args.targets, args.action)
    except ValueError as e:
        logger.critical(f"Invalid images file: {e}")
        exit(1)
    prefix = (
        args.tag_prefix
        if args.tag_prefix is not None
        else os.environ.get("TAG_PREFIX", "")
    )
    return args.func(
        images_data,
        targets,
        dry_run=args.dry_run,
        show_progress=show_progress,
        prefix=prefix,
    )


if __name__ == "__main__":
    sys.exit(main())
