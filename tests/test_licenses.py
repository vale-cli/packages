import io
import json
import zipfile

import requests

from . import get_library


def test_declared_license_files_exist():
    """A package that declares `license_files` in its `meta.json` must ship
    those files in its archive.

    The declaration is optional -- a package without one passes -- but a
    declared path that's missing from the zip is a broken promise to
    downstream repackagers, who rely on it for attribution.
    """
    for entry in get_library():
        r = requests.get(entry["url"], allow_redirects=True, timeout=60)
        assert r.status_code == 200, f"{entry['name']}: {entry['url']}"

        archive = zipfile.ZipFile(io.BytesIO(r.content))
        names = set(archive.namelist())

        meta_path = f"{entry['name']}/meta.json"
        if meta_path not in names:
            continue

        meta = json.loads(archive.read(meta_path))

        for declared in meta.get("license_files", []):
            path = f"{entry['name']}/{declared}"
            assert path in names, f"{entry['name']}: missing {path}"
