# PyPI Trusted Publishing Setup

This guide sets up **OIDC Trusted Publishing** so GitHub Actions can push to
PyPI without storing a long-lived token.

## One-time PyPI setup (per package)

1. Go to **https://pypi.org/manage/account/publishing/**
2. Add a new trusted publisher for each package:

| Field | Value |
|---|---|
| PyPI project name | `mcp-fhir` (or `mcp-terminology`, `mcp-clinical-reasoner`) |
| GitHub owner | `pcmedsinge` |
| GitHub repo | `fhir-mcp-suite` |
| Workflow file | `release.yml` |
| Environment | `pypi` |

3. Repeat for `mcp-terminology` and `mcp-clinical-reasoner` when ready.

## GitHub setup

1. In the repo → **Settings → Environments**, create environment named **`pypi`**.
2. Add a protection rule: require a specific branch (`main`) and optionally require
   a manual reviewer for production releases.

## Triggering a release

```bash
# Make sure version in pyproject.toml matches the tag
git tag mcp-fhir-v1.0.0
git push origin mcp-fhir-v1.0.0
```

The `release.yml` workflow will:
1. Extract package name + version from the tag
2. Assert `pyproject.toml` version matches
3. Build wheel + sdist
4. Publish via OIDC (no token needed)
5. Create a GitHub Release with the built artefacts

## Verifying after publish

```bash
pip install mcp-fhir==1.0.0
mcp-fhir --help
# Or via uvx (no install):
uvx mcp-fhir --help
```

## Install badge (add to README)

```markdown
[![PyPI version](https://badge.fury.io/py/mcp-fhir.svg)](https://badge.fury.io/py/mcp-fhir)
```
