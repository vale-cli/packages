"""Run the templates, filters, vocabularies, scripts, and actions through Vale.

These need a Vale binary: `vale` on the PATH, or the path in VALE. Without
one, they're skipped.
"""
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
OUTPUTS = os.path.join(FIXTURES, "outputs")
RULES = os.path.join(FIXTURES, "rules", "Assets")

VALE = os.environ.get("VALE") or shutil.which("vale")

pytestmark = pytest.mark.skipif(
    not VALE or not os.path.isfile(VALE), reason="vale isn't on the PATH (set VALE)"
)


def asset(kind, name):
    return os.path.join(ASSETS, kind, name)


def names(kind, ext):
    return sorted(
        f[: -len(ext)] for f in os.listdir(os.path.join(ASSETS, kind)) if f.endswith(ext)
    )


def vale(*args, cwd=OUTPUTS):
    """Run Vale, failing on anything but a clean run or one with errors."""
    run = subprocess.run(
        [VALE, "--no-global", *args], cwd=cwd, capture_output=True, text=True
    )
    assert run.returncode in (0, 1), run.stderr or run.stdout
    return run.stdout


def alerts(*args):
    """The fixture's alerts as JSON, [(path, alert), ...]."""
    out = json.loads(vale("--output=JSON", *args, "doc.md", "clean.md"))
    return [(path, a) for path, found in out.items() for a in found]


def render(template):
    return vale(f"--output={asset('templates', template + '.tmpl')}", "doc.md", "clean.md")


# Templates


def test_fixture_covers_every_level():
    levels = {a["Severity"] for _, a in alerts()}
    assert levels == {"error", "warning", "suggestion"}


def test_gitlab():
    issues = json.loads(render("gitlab"))
    want = alerts()
    assert len(issues) == len(want)
    for issue, (path, a) in zip(issues, want):
        assert issue["check_name"] == a["Check"]
        assert issue["description"] == a["Message"]
        assert issue["location"] == {"path": path, "lines": {"begin": a["Line"]}}
        assert issue["severity"] in {"info", "minor", "major", "critical", "blocker"}
        assert re.fullmatch(r"[0-9a-f]{64}", issue["fingerprint"])

    levels = {a["Severity"]: i["severity"] for i, (_, a) in zip(issues, want)}
    assert levels == {"error": "major", "warning": "minor", "suggestion": "info"}

    # Unique per alert, and the same on the next run.
    prints = [i["fingerprint"] for i in issues]
    assert len(set(prints)) == len(prints)
    assert prints == [i["fingerprint"] for i in json.loads(render("gitlab"))]


def test_gitlab_empty():
    out = vale(f"--output={asset('templates', 'gitlab.tmpl')}", "clean.md")
    assert json.loads(out) == []


def test_junit():
    root = ET.fromstring(render("junit"))
    want = alerts()
    failing = [a for _, a in want if a["Severity"] != "suggestion"]

    assert root.tag == "testsuites"
    assert root.get("tests") == str(len(want))
    assert root.get("failures") == str(len(failing))

    suites = root.findall("testsuite")
    assert [s.get("name") for s in suites] == sorted({p for p, _ in want})

    cases = [c for s in suites for c in s.findall("testcase")]
    assert len(cases) == len(want)
    for case, (path, a) in zip(cases, want):
        assert case.get("name") == a["Check"]
        failure = case.find("failure")
        if a["Severity"] == "suggestion":
            assert failure is None
        else:
            assert failure.get("type") == a["Severity"]
            # The message carries quotes, <, >, and &, so this only parses
            # when they're escaped.
            assert failure.get("message") == a["Message"]


def test_junit_empty():
    out = vale(f"--output={asset('templates', 'junit.tmpl')}", "clean.md")
    root = ET.fromstring(out)
    assert root.get("tests") == "0" and len(root) == 0


def test_sarif():
    log = json.loads(render("sarif"))
    want = alerts()
    assert log["version"] == "2.1.0"
    assert log["$schema"].endswith("sarif-2.1.0.json")

    run = log["runs"][0]
    rules = [r["id"] for r in run["tool"]["driver"]["rules"]]
    assert sorted(rules) == sorted({a["Check"] for _, a in want})

    results = run["results"]
    assert len(results) == len(want)
    levels = {"error": "error", "warning": "warning", "suggestion": "note"}
    for r, (path, a) in zip(results, want):
        assert r["ruleId"] == a["Check"]
        assert r["level"] == levels[a["Severity"]]
        assert r["message"]["text"] == a["Message"]
        loc = r["locations"][0]["physicalLocation"]
        assert loc["artifactLocation"]["uri"] == path
        assert loc["region"]["startLine"] == a["Line"]
        assert loc["region"]["startColumn"] == a["Span"][0]
        assert loc["region"]["endColumn"] == a["Span"][1] + 1
        assert loc["region"]["snippet"]["text"] == a["Match"]


def test_sarif_empty():
    out = vale(f"--output={asset('templates', 'sarif.tmpl')}", "clean.md")
    run = json.loads(out)["runs"][0]
    assert run["results"] == [] and run["tool"]["driver"]["rules"] == []


def test_rdjsonl():
    lines = render("rdjsonl").splitlines()
    want = alerts()
    assert len(lines) == len(want)
    levels = {"error": "ERROR", "warning": "WARNING", "suggestion": "INFO"}
    for line, (path, a) in zip(lines, want):
        d = json.loads(line)
        assert d["message"] == a["Message"]
        assert d["severity"] == levels[a["Severity"]]
        assert d["code"]["value"] == a["Check"]
        assert d["location"]["path"] == path
        assert d["location"]["range"]["start"] == {"line": a["Line"], "column": a["Span"][0]}
        assert d["location"]["range"]["end"] == {"line": a["Line"], "column": a["Span"][1] + 1}
        if a["Link"]:
            assert d["code"]["url"] == a["Link"]


# Filters


@pytest.mark.parametrize(
    "name, checks",
    [
        ("errors", {"Test.Obviously", "Vale.Spelling"}),
        ("no-spelling", {"Test.Obviously", "Test.Utilize", "Test.Should", "Test.Spelling"}),
        ("no-suggestions", {"Test.Obviously", "Test.Utilize", "Test.Spelling", "Vale.Spelling"}),
        ("spelling", {"Test.Spelling", "Vale.Spelling"}),
    ],
)
def test_filter(name, checks):
    found = alerts(f"--filter={asset('filters', name + '.expr')}")
    assert {a["Check"] for _, a in found} == checks


# Vocabularies


def expand(entry):
    """Every spelling an entry accepts, for the simple patterns used here."""
    m = re.search(r"\[([^\]]+)\]|(.)\?", entry)
    if not m:
        return [entry]
    head, tail = entry[: m.start()], entry[m.end():]
    if m.group(1):
        options = list(m.group(1))
    else:
        options = ["", m.group(2)]
    return [w for o in options for w in expand(head + o + tail)]


def spelling(tmp_path, words, vocab=None):
    """The words Vale.Spelling flags, with or without the vocabulary."""
    styles = tmp_path / "styles"
    (styles / "config" / "vocabularies").mkdir(parents=True, exist_ok=True)
    ini = "StylesPath = styles\n"
    if vocab:
        dest = styles / "config" / "vocabularies" / vocab
        if not dest.exists():
            shutil.copytree(os.path.join(ASSETS, "vocabularies", vocab), dest)
        ini += f"Vocab = {vocab}\n"
    ini += "\n[*.md]\nBasedOnStyles = Vale\n"
    (tmp_path / ".vale.ini").write_text(ini)
    (tmp_path / "terms.md").write_text("".join(f"Use {w} here.\n\n" for w in words))

    out = json.loads(
        vale("--output=JSON", "--filter=.Name == 'Vale.Spelling'", "terms.md", cwd=tmp_path)
    )
    return {a["Match"] for found in out.values() for a in found}


@pytest.mark.parametrize("name", sorted(os.listdir(os.path.join(ASSETS, "vocabularies"))))
def test_vocabulary(tmp_path, name):
    with open(os.path.join(ASSETS, "vocabularies", name, "accept.txt")) as f:
        entries = [e.strip() for e in f if e.strip() and not e.startswith("# ")]
    assert entries == sorted(entries, key=lambda e: re.sub(r"\[(.).*?\]", r"\1", e).lower())

    forms = {e: expand(e) for e in entries}
    words = [w for ws in forms.values() for w in ws]

    # Each entry is one the dictionary gets wrong on its own.
    flagged = spelling(tmp_path, words)
    for entry, ws in forms.items():
        assert flagged & set(ws), f"{entry}: the dictionary already accepts it"

    assert spelling(tmp_path, words, vocab=name) == set()


# Scripts and actions


def test_every_script_and_action_has_cases():
    rules = {f[:-4] for f in os.listdir(RULES) if f.endswith(".yml")}
    assert set(names("scripts", ".tengo")) | set(names("actions", ".tengo")) <= rules


@pytest.mark.parametrize("rule", sorted(f for f in os.listdir(RULES) if f.endswith(".yml")))
def test_rule_cases(tmp_path, rule):
    """Each fixture rule's `tests`, run against the asset as installed."""
    styles = tmp_path / "styles"
    shutil.copytree(RULES, styles / "Assets")
    shutil.copytree(os.path.join(ASSETS, "scripts"), styles / "config" / "scripts")
    shutil.copytree(os.path.join(ASSETS, "actions"), styles / "config" / "actions")
    (tmp_path / ".vale.ini").write_text("StylesPath = styles\n")

    run = subprocess.run(
        [VALE, "test", f"styles/Assets/{rule}"], cwd=tmp_path, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stdout + run.stderr
