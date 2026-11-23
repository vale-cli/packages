"""Each view exposes only the text it names, at the lines it came from.

Set VALE to the binary to test with; without one on PATH, these are skipped.
"""
import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEWS = os.path.join(ROOT, "assets", "views")
FIXTURES = os.path.join(ROOT, "tests", "fixtures", "views")

VALE = os.environ.get("VALE") or shutil.which("vale")
if not VALE or not os.access(VALE, os.X_OK):
    pytest.skip("vale is not installed; set VALE to its path", allow_module_level=True)

# (view, fixture, the (line, check, match) each alert must be).
CASES = [
    ("I18nJSON", "I18nJSON.json", {
        (3, "Vale.Repetition", "the the"),
        (7, "Vale.Spelling", "Recieve"),
        (10, "Vale.Spelling", "Mondey"),
    }),
    ("I18nYAML", "I18nYAML.yml", {
        (3, "Vale.Repetition", "the the"),
        (7, "Vale.Spelling", "Recieve"),
    }),
    ("AndroidStrings", "AndroidStrings.xml", {
        (4, "Vale.Repetition", "the the"),
        (6, "Vale.Spelling", "Recieve"),
        (8, "Vale.Spelling", "mispelled"),
        (9, "Vale.Repetition", "are are"),
    }),
    ("AppleStrings", "AppleStrings.strings", {
        (2, "Vale.Repetition", "the the"),
        (5, "Vale.Spelling", "Recieve"),
        (6, "Vale.Spelling", "teh"),
    }),
    ("JSONSchema", "JSONSchema.schema.json", {
        (3, "Vale.Spelling", "teh"),
        (4, "Vale.Repetition", "the the"),
        (9, "Vale.Spelling", "recieved"),
        (14, "Vale.Spelling", "Recieve"),
    }),
    ("JSONSchema", "JSONSchema.schema.yml", {
        (2, "Vale.Spelling", "teh"),
        (3, "Vale.Repetition", "the the"),
        (8, "Vale.Spelling", "recieved"),
        (11, "Vale.Spelling", "Recieve"),
    }),
    ("CRD", "CRD.yaml", {
        (16, "Vale.Repetition", "the the"),
        (22, "Vale.Spelling", "mispelled"),
        (27, "Vale.Spelling", "recieve"),
        (32, "Vale.Spelling", "teh"),
    }),
    ("GraphQL", "GraphQL.graphql", {
        (4, "Vale.Repetition", "the the"),
        (7, "Vale.Spelling", "recieved"),
        (10, "Vale.Spelling", "teh"),
        (15, "Vale.Spelling", "mispelled"),
    }),
    ("WebVTT", "WebVTT.vtt", {
        (11, "Vale.Repetition", "the the"),
        (16, "Vale.Spelling", "mispelled"),
        (19, "Vale.Spelling", "Recieve"),
    }),
]


def lint(tmp_path, view, fixture):
    """Lint a copy of the fixture with only the view's section configured."""
    styles = tmp_path / "styles" / "config" / "views"
    styles.mkdir(parents=True)
    shutil.copy(os.path.join(VIEWS, view + ".yml"), styles)
    shutil.copy(os.path.join(FIXTURES, fixture), tmp_path)
    (tmp_path / ".vale.ini").write_text(
        f"StylesPath = styles\n\n[{fixture}]\nBasedOnStyles = Vale\nView = {view}\n"
    )
    out = subprocess.run(
        [VALE, "--output=JSON", "--no-exit", fixture],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr or out.stdout
    alerts = json.loads(out.stdout or "{}")
    return [a for file_alerts in alerts.values() for a in file_alerts]


@pytest.mark.parametrize("view, fixture, want", CASES, ids=[c[1] for c in CASES])
def test_view(tmp_path, view, fixture, want):
    """Alerts land on the exposed text only, at the expected lines."""
    got = {(a["Line"], a["Check"], a["Match"]) for a in lint(tmp_path, view, fixture)}
    assert got == want

