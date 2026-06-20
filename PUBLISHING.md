# MCP Server Publishing Guide

> Complete step-by-step guide for publishing Python MCP servers from this monorepo.  
> Written from experience publishing `fhir-mcp-suite` (June 2026).

---

## Overview

Publishing one MCP server involves 4 stages:

1. **PyPI setup** — one-time account + trusted publisher configuration
2. **Code prep** — add `mcp-name` marker + bump version
3. **Release** — git tag → GitHub Actions → PyPI automatically
4. **Registry listing** — MCP Registry + Smithery + Glama

For a **monorepo with multiple packages**, do stages 1–3 for each package one at a time (PyPI rate-limits new publisher registrations to ~1/day).

---

## Stage 1 — PyPI Setup (one-time per package, one per day)

### 1.1 Create a PyPI account (once ever)

1. Go to https://pypi.org/account/register/
2. Fill in username, email, password
3. Verify your email

### 1.2 Enable 2FA (mandatory for publishers)

1. Go to https://pypi.org/manage/account/#two-factor
2. Click **Add 2FA with authentication app**
3. Scan QR code with Google Authenticator / Microsoft Authenticator / Authy
4. Enter the 6-digit code to confirm
5. **Save the recovery codes** somewhere safe

### 1.3 Register a trusted publisher for the package

> Do this **one package per day** — PyPI rate-limits pending publisher creation.

1. Go to https://pypi.org/manage/account/publishing/
2. Stay on the **GitHub** tab
3. Fill in the form:
   - **Pending project name**: e.g. `mcp-fhir`
   - **Owner**: `pcmedsinge`  (your GitHub username)
   - **Repository name**: `fhir-mcp-suite`
   - **Workflow filename**: `release.yml`
   - **Environment name**: `pypi`  ← **must fill this in**
4. Click **Add**
5. Repeat the next day for the next package

**For this repo, packages to register (in order):**

| Day | Package |
|-----|---------|
| Day 1 | `fhir-mcp-shared` |
| Day 2 | `mcp-fhir` |
| Day 3 | `mcp-terminology` |
| Day 4 | `mcp-clinical-reasoner` |

> **Important**: `fhir-mcp-shared` must be published first because the other 3 depend on it.

### 1.4 Create the `pypi` GitHub environment (once ever)

1. Go to https://github.com/pcmedsinge/fhir-mcp-suite/settings/environments
2. Click **New environment**
3. Name: `pypi` (exactly, lowercase)
4. Click **Configure environment**
5. Under "Deployment branches", select **Selected branches** → add `main`
6. Click **Save protection rules**

---

## Stage 2 — Code Prep (per package, before first release)

### 2.1 Add the `mcp-name` marker to the package README

The MCP Registry requires this HTML comment in the package README for PyPI packages.

Edit `packages/<pkg>/README.md` — add this **immediately after the H1 title**:

```markdown
# mcp-fhir

<!-- mcp-name: io.github.pcmedsinge/mcp-fhir -->

> rest of README...
```

Use the correct name for each package:
- `mcp-fhir` → `<!-- mcp-name: io.github.pcmedsinge/mcp-fhir -->`
- `mcp-terminology` → `<!-- mcp-name: io.github.pcmedsinge/mcp-terminology -->`
- `mcp-clinical-reasoner` → `<!-- mcp-name: io.github.pcmedsinge/mcp-clinical-reasoner -->`

### 2.2 Check the version number

Confirm the version in `packages/<pkg>/pyproject.toml` matches what you want to release:

```toml
version = "1.0.0"
```

Commit and push any changes before tagging.

---

## Stage 3 — Release to PyPI (per package)

### 3.1 Tag the release

```bash
# Replace <pkg> and <version> with actual values
git tag <pkg>-v<version>
git push origin <pkg>-v<version>

# Examples:
git tag fhir-mcp-shared-v0.1.0
git push origin fhir-mcp-shared-v0.1.0

git tag mcp-fhir-v1.1.1
git push origin mcp-fhir-v1.1.1

git tag mcp-terminology-v1.0.0
git push origin mcp-terminology-v1.0.0

git tag mcp-clinical-reasoner-v1.0.0
git push origin mcp-clinical-reasoner-v1.0.0
```

> The tag format **must exactly match** the `release.yml` trigger patterns:
> `mcp-fhir-v*`, `mcp-terminology-v*`, `mcp-clinical-reasoner-v*`, `fhir-mcp-shared-v*`

### 3.2 Watch the release workflow

Go to: https://github.com/pcmedsinge/fhir-mcp-suite/actions/workflows/release.yml

You should see a new run triggered by the tag. It will:
1. Parse the package name and version from the tag
2. Verify `pyproject.toml` version matches the tag
3. Build wheel + sdist
4. Publish to PyPI via OIDC (no password needed)
5. Create a GitHub Release with the `.whl` attached

Takes ~60–90 seconds.

### 3.3 Verify on PyPI

After the workflow goes green, check:
- https://pypi.org/project/mcp-fhir/
- https://pypi.org/project/mcp-terminology/
- https://pypi.org/project/mcp-clinical-reasoner/
- https://pypi.org/project/fhir-mcp-shared/

Test install:
```bash
pip install mcp-fhir
# or without installing:
uvx mcp-fhir
```

### 3.4 Handle common failures

| Error | Cause | Fix |
|-------|-------|-----|
| `Install build deps` step fails | `uv pip install` doesn't work in release context | Use `pip install` — already fixed in this repo's `release.yml` |
| `Version mismatch` error | Tag version differs from `pyproject.toml` | Delete tag, fix version, retag |
| PyPI 400 — package not found | PyPI pending publisher not registered | Register at pypi.org/manage/account/publishing/ |
| Release workflow never triggers | `concurrency: cancel-in-progress: true` cancelled it | Push an empty commit to re-trigger |
| PyPI email warning about environment | Publisher registered without environment name | Go to project's publishing settings, delete and re-add with `pypi` as environment |

**To delete and retag:**
```bash
git tag -d mcp-fhir-v1.1.0              # delete local tag
git push origin --delete mcp-fhir-v1.1.0 # delete remote tag
# fix the issue, then:
git tag mcp-fhir-v1.1.0
git push origin mcp-fhir-v1.1.0
```

---

## Stage 4 — Register on MCP Registry

### 4.1 Download `mcp-publisher` CLI (Windows)

Run in PowerShell:
```powershell
$arch = if ([System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -eq "Arm64") { "arm64" } else { "amd64" }
Invoke-WebRequest -Uri "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_windows_$arch.tar.gz" -OutFile "mcp-publisher.tar.gz"
tar xf mcp-publisher.tar.gz mcp-publisher.exe
Remove-Item mcp-publisher.tar.gz
```

Verify:
```powershell
.\mcp-publisher.exe --help
```

### 4.2 Create `server.json` for each package

Run in the package directory:
```powershell
Set-Location packages\mcp-fhir
& "e:\PracticeApps\AIRelated\MCP\fhir-mcp-suite\mcp-publisher.exe" init
```

Edit the generated `server.json`. Key rules:
- `name` must be `io.github.pcmedsinge/<package-name>`
- `description` **must be ≤ 100 characters**
- `version` must match what's on PyPI
- `registryType` must be `"pypi"`
- `identifier` is the PyPI package name
- Remove the `YOUR_API_KEY` env var placeholder if the package has no required secrets

**Template for this repo:**

```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json",
  "name": "io.github.pcmedsinge/mcp-fhir",
  "description": "FHIR R4 read/search/validate MCP server — US Core/IPS profiles, SMART-on-FHIR auth (Epic/Cerner).",
  "repository": {
    "url": "https://github.com/pcmedsinge/fhir-mcp-suite",
    "source": "github",
    "subfolder": "packages/mcp-fhir"
  },
  "version": "1.1.1",
  "packages": [
    {
      "registryType": "pypi",
      "identifier": "mcp-fhir",
      "version": "1.1.1",
      "transport": {
        "type": "stdio"
      },
      "environmentVariables": [
        {
          "description": "Base URL of the FHIR R4 server (default: https://hapi.fhir.org/baseR4)",
          "isRequired": false,
          "format": "string",
          "isSecret": false,
          "name": "FHIR_BASE_URL"
        }
      ]
    }
  ]
}
```

### 4.3 Login to MCP Registry

```powershell
& "e:\PracticeApps\AIRelated\MCP\fhir-mcp-suite\mcp-publisher.exe" login github
```

It will print a device code and a URL. Go to https://github.com/login/device, enter the code, authorize. Login persists — you only need to do this once per machine.

### 4.4 Publish to MCP Registry

```powershell
Set-Location packages\mcp-fhir
& "e:\PracticeApps\AIRelated\MCP\fhir-mcp-suite\mcp-publisher.exe" publish
```

Repeat for each package (no need to login again):
```powershell
Set-Location ..\mcp-terminology
& "e:\PracticeApps\AIRelated\MCP\fhir-mcp-suite\mcp-publisher.exe" publish

Set-Location ..\mcp-clinical-reasoner
& "e:\PracticeApps\AIRelated\MCP\fhir-mcp-suite\mcp-publisher.exe" publish
```

### 4.5 Verify on MCP Registry

https://registry.modelcontextprotocol.io/?search=io.github.pcmedsinge

Or via API:
```bash
curl "https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.pcmedsinge"
```

### 4.6 Handle common failures

| Error | Cause | Fix |
|-------|-------|-----|
| `expected length <= 100` on description | Description too long | Shorten to ≤ 100 chars in `server.json` |
| `PyPI package not found (status: 404)` | Package not yet on PyPI or PyPI slow to index | Wait 2–5 min then retry |
| `You do not have permission to publish` | Auth doesn't match namespace | Must use GitHub login; name must start with `io.github.pcmedsinge/` |
| `Invalid or expired Registry JWT token` | Auth expired | Run `mcp-publisher login github` again |
| `registry validation failed` — mcp-name not found | `mcp-name` comment not in published README | Re-release package with comment in README |

---

## Stage 5 — Other Discovery Platforms

### Smithery
1. Go to https://smithery.ai
2. Look for "Submit server" button
3. Provide GitHub repo URL and package details

### Glama
1. Go to https://glama.ai/mcp/servers
2. Submit your server for listing

---

## Stage 5 — Glama (glama.ai/mcp/servers)

Glama is an MCP server directory that auto-indexes GitHub repos and runs quality checks.
Servers that pass quality checks appear in search results.

### 5.1 Submit the server

1. Go to https://glama.ai/mcp/servers
2. Click **Add Server** (top right)
3. Fill in the form:
   - **Name**: `fhir-mcp-suite`
   - **Description**: Three composable MCP servers for clinical AI — FHIR R4 read/search/validate, medical terminology (LOINC/SNOMED/RxNorm/ICD-10), and drug safety reasoning (interactions, dose check, allergy). Apache-2.0, production-ready.
   - **GitHub Repository URL**: `https://github.com/pcmedsinge/fhir-mcp-suite`
4. Click **Submit for Review** — Glama reviews manually, typically 1–3 days
5. You will receive an email when approved

### 5.2 Claim the server (after approval email)

1. Log in to Glama with your GitHub account (`pcmedsinge`)
2. Go to https://glama.ai/mcp/servers/pcmedsinge/fhir-mcp-suite
3. Look for **Claim this server** — only visible when logged in
4. If not visible, go directly to: https://glama.ai/mcp/servers/pcmedsinge/fhir-mcp-suite/admin

### 5.3 Configure the Dockerfile for quality checks

> This is required to appear in Glama search results.  
> Glama uses this to run automated safety and quality checks — it does NOT need to be in your repo.

Go to: https://glama.ai/mcp/servers/pcmedsinge/fhir-mcp-suite/admin/dockerfile

Fill in the form:
- **Base image**: `debian:trixie-slim` (default)
- **Node.js version**: `26` (default)
- **Python version**: `3.12`
- **Build steps**: `[]` (empty)
- **CMD arguments**: `["uv", "run", "--with", "mcp-fhir", "mcp-fhir"]`
- **Environment variables JSON schema**: leave as auto-detected
- **Placeholder parameters**: `{"FHIR_BASE_URL": "https://hapi.fhir.org/baseR4"}`
- **Pinned commit SHA**: leave as current head (or empty for latest)

Click **Build** first to test. If green, click **Build & Release**.

The Dockerfile Glama generates will look like:
```dockerfile
FROM debian:trixie-slim
ENV DEBIAN_FRONTEND=noninteractive GLAMA_VERSION="1.0.0" PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y ... && uv python install 3.12 ...
WORKDIR /app
RUN git clone https://github.com/pcmedsinge/fhir-mcp-suite . && git checkout <sha>
CMD ["mcp-proxy","--","uv","run","--with","mcp-fhir","mcp-fhir"]
```

The `mcp-proxy` wrapper Glama adds is how they inspect stdio servers — your server is unchanged.

### 5.4 Common failures

| Error | Cause | Fix |
|-------|-------|-----|
| `pip: not found` | Glama image uses uv, not pip | Use `uv pip install --system` in build steps, or skip build steps and use CMD with `uv run` |
| `externally managed environment` | System Python is protected | Don't use `--system`; use `["uv", "run", "--with", "mcp-fhir", "mcp-fhir"]` in CMD instead |
| `CMD cannot contain ['uvx']` | Glama blocks uvx alias | Use `["uv", "run", "--with", "mcp-fhir", "mcp-fhir"]` |
| Placeholder parameters mismatch | Required env var not provided | Add `{"FHIR_BASE_URL": "https://hapi.fhir.org/baseR4"}` to placeholder params |

---

## Updating an existing release

When you make code changes and want to release a new version:

1. Bump version in `packages/<pkg>/pyproject.toml`
2. Update `packages/<pkg>/server.json` version to match
3. Commit and push
4. Tag and push: `git tag mcp-fhir-v1.1.2 && git push origin mcp-fhir-v1.1.2`
5. After PyPI release goes green, update MCP Registry:
   ```powershell
   Set-Location packages\mcp-fhir
   & "e:\...\mcp-publisher.exe" publish
   ```

---

## Quick reference — all package names

| pyproject.toml `name` | PyPI URL | Tag format | MCP Registry name |
|----------------------|----------|------------|-------------------|
| `fhir-mcp-shared` | pypi.org/project/fhir-mcp-shared | `fhir-mcp-shared-vX.Y.Z` | *(internal, not listed)* |
| `mcp-fhir` | pypi.org/project/mcp-fhir | `mcp-fhir-vX.Y.Z` | `io.github.pcmedsinge/mcp-fhir` |
| `mcp-terminology` | pypi.org/project/mcp-terminology | `mcp-terminology-vX.Y.Z` | `io.github.pcmedsinge/mcp-terminology` |
| `mcp-clinical-reasoner` | pypi.org/project/mcp-clinical-reasoner | `mcp-clinical-reasoner-vX.Y.Z` | `io.github.pcmedsinge/mcp-clinical-reasoner` |

---

## Adding uv to PATH on Windows (one-time)

After `pip install uv`, find where it landed and add to PATH permanently:

```powershell
# Find uv.exe
Get-ChildItem "C:\Users\$env:USERNAME\AppData\Local\Python" -Recurse -Filter "uv.exe" | Select-Object FullName

# Add that Scripts folder to user PATH permanently
$uvScripts = "C:\Users\$env:USERNAME\AppData\Local\Python\pythoncore-3.XX-64\Scripts"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$uvScripts", "User")
# Restart terminal — then `uv` works directly
```
