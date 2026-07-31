import requests

from . import get_library


REQUIRED = {"name", "description", "homepage", "url"}
OPTIONAL = {"logo", "tags"}


def test_keys():
    """Ensure that all required keys are defined.
    """
    for entry in get_library():
        keys = set(entry.keys())
        assert REQUIRED <= keys, entry.get("name")
        assert keys <= REQUIRED | OPTIONAL, entry.get("name")


def test_links():
    """Ensure that our all links are working.
    """
    for entry in get_library():
        for k in ("homepage", "url"):
            link = entry[k]
            # Follow redirects and judge the destination: the errata-ai to
            # vale-cli rename means GitHub answers 301 for every legacy entry,
            # which is a working link and not a broken one.
            r = requests.head(link, allow_redirects=True, timeout=15)
            assert r.status_code == 200, f"{entry['name']} {k}: {link} -> {r.status_code}"
