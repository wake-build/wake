from wake_build.config import get_dependency_targets


images_data = [
    {
        "name": "image1",
        "tag": "latest",
        "dependencies": [
            {"name": "image2", "tag": "latest"},
            {"name": "image4", "tag": "latest"},
        ],
        "actions": ["build"],
    },
    {
        "name": "image2",
        "tag": "latest",
        "dependencies": [
            {"name": "image3", "tag": "latest"},
        ],
        "actions": ["build"],
    },
    {
        "name": "image3",
        "tag": "latest",
        "dependencies": [],
        "actions": ["pull"],
    },
    {
        "name": "image4",
        "tag": "latest",
        "dependencies": [],
        "actions": ["pull"],
    },
]


def test_get_target_dependencies_build():
    target = ("image1", "latest")
    expected = {("image1", "latest"), ("image2", "latest")}
    result = get_dependency_targets(images_data, target, "build")
    assert result == expected, f"Expected {expected}, but got {result}"


def test_get_target_dependencies_pull():
    target = ("image1", "latest")
    expected = {("image3", "latest"), ("image4", "latest")}
    result = get_dependency_targets(images_data, target, "pull")
    assert result == expected, f"Expected {expected}, but got {result}"
