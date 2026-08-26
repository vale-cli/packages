# Packages

The package registry for [Vale](https://vale.sh). [`library.json`](library.json) lists every package Vale can install by name, and is what the [Package Explorer](https://vale.sh/explorer) is built from.

Browse the packages at **[vale.sh/explorer](https://vale.sh/explorer)**, where each one is listed with its description and the rules it contains.

## Using a package

Name it under `Packages` in your `.vale.ini` and run `vale sync`:

```ini
StylesPath = styles

Packages = Microsoft

[*.md]
BasedOnStyles = Microsoft
```

Packages fall into two kinds. A *style* is a set of rules to check prose against. A *config* adds support for markup a format needs, and is combined with whatever style you are already using.

### Pinning a version

Naming a package installs its latest release, so the rules you get can change as the package is updated. To stay on a known version, give the release URL instead of the name:

```ini
Packages = https://github.com/vale-cli/Google/releases/download/v0.7.0/Google.zip
```

The style keeps the name of the directory inside the archive, so `BasedOnStyles` stays the same either way. Pinning is worth doing where a new rule appearing on its own would be disruptive — shared repositories, and CI that fails on new alerts.

Several are Vale implementations of existing linters. Using them means [better handling of markup](https://docs.vale.sh/topics/scopes) — code blocks skipped, rules aimed at particular sections — no npm or pip to install alongside Vale, and the freedom to mix rules from several packages in one configuration.

## Submitting a package

Fork this repo, add an entry to [`library.json`](library.json), and open a pull request:

```json
{
    "name": "Example",
    "description": "A short sentence describing what it checks.",
    "homepage": "https://github.com/you/Example",
    "url": "https://github.com/you/Example/releases/latest/download/Example.zip",
    "logo": "https://github.com/you.png",
    "tags": [
        "style"
    ]
}
```

Entries are ordered by `name`, and `url` should point at a release asset whose archive contains a single directory matching `name`. Tag it `style` or `config`; further tags may be added to describe what it covers. `logo` is optional and defaults to nothing.

### Shipping license files

Downstream distributors—package managers repackaging these archives—need attribution documents inside the archive itself, not just in the repository. To support that, ship your license alongside the rules and declare it in the style's `meta.json`:

```json
{
    "license_files": ["LICENSE"]
}
```

Each declared path is relative to the style directory, and the checks verify it exists in the released archive. The declaration is optional, but a declared file that's missing fails the check.

Opening the pull request runs the checks described below.

## Security

Listing a package here is what lets Vale install it by name, so entries are reviewed rather than merged automatically.

- What each pull request has to pass: Adding or repointing an entry downloads that package and loads it into Vale, which confirms its rules compile. Separately, `library.json` is checked for valid JSON, the expected keys on every entry, alphabetical order, and a working `homepage` and `url`.

- What a package is: A directory of YAML rules. Most describe patterns to look for. A rule may also carry a `script` or a `metric` formula, which Vale evaluates in an embedded interpreter given a deliberately small set of imports: rule code can read the text it is checking and compute, and has no access to the filesystem, the network, or the host process.

- What listing does not promise: Each `url` points at a project's latest release, so a package's rules can change after it is added. Review establishes what a package checked when it was listed, not what it will check later. That is a question about results rather than about safety: what a package decides is which alerts you see, and the paragraph above is the extent of it. [Pinning a version](#pinning-a-version) holds a package at a release you have already seen.

- If something looks wrong: Open an issue here, and contact the package's own maintainers through its `homepage`. If an entry should no longer be listed, say so in the issue and it can be removed.
