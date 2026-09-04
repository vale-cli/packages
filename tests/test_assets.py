import json
import os

from . import get_library

REQUIRED = {"name", "kind", "description", "path"}
OPTIONAL = {"requires", "tags", "section"}
KINDS = {"view", "filter", "script", "action", "vocabulary", "template"}


def get_assets():
    with open("assets.json") as f:
        return json.load(f)


def test_asset_keys():
    """Every asset states what it is and where it lives."""
    for entry in get_assets():
        keys = set(entry.keys())
        assert REQUIRED <= keys, entry.get("name")
        assert keys <= REQUIRED | OPTIONAL, entry.get("name")
        assert entry["kind"] in KINDS, entry.get("name")


def test_asset_order():
    """Assets are sorted by kind, then name, so a diff stays readable."""
    keys = [(e["kind"], e["name"]) for e in get_assets()]
    assert keys == sorted(keys)


def test_asset_files():
    """Every listed path exists, and a view names an engine and its scopes."""
    for entry in get_assets():
        assert os.path.isfile(entry["path"]), entry["path"]
        if entry["kind"] == "view":
            with open(entry["path"]) as f:
                view = f.read()
            assert "\nengine: " in view or view.startswith("engine: "), entry["path"]
            assert "\nscopes:" in view, entry["path"]
            assert entry.get("section"), f"{entry['name']}: a view names the section it applies to"


def test_assets_are_not_packages():
    """An asset is a file to copy, not a package to sync: no name collides."""
    packages = {e["name"] for e in get_library()}
    for entry in get_assets():
        assert entry["name"] not in packages, entry["name"]
