# Onboarding Any GitHub Repo — Cross-Platform Setup Guide

> Works on **Linux · macOS · Windows**  
> Covers Python (uv, pip, venv), Node.js (npm, pnpm), and general patterns.  
> Follow this every time you clone a repo someone else developed.

---

## Step 1 — Read the repo before touching anything

| File to look for | What it tells you |
|---|---|
| `README.md` | Quick-start instructions, prerequisites |
| `pyproject.toml` | Python project: deps, build system, scripts |
| `package.json` | Node.js project: deps, scripts |
| `uv.lock` | Python managed by **uv** → use `uv sync` |
| `poetry.lock` | Python managed by **Poetry** → use `poetry install` |
| `Pipfile.lock` | Python managed by **Pipenv** → use `pipenv install` |
| `requirements.txt` | Plain pip → use `pip install -r requirements.txt` |
| `docker-compose.yml` | Services (DB, APIs) needed alongside the code |
| `.env.example` | Env vars you must set before running |
| `.python-version` / `.nvmrc` | Pinned runtime version |

**Never run `pip install` or `npm install` before reading these.** Wrong tool = broken install.

---

## Step 2 — Install the right runtime version

### Python

```bash
# Check what version the project requires
# Look in pyproject.toml → requires-python = ">=3.12"
# or .python-version file

# Linux/macOS — use pyenv
pyenv install 3.12
pyenv local 3.12        # writes .python-version in project dir

# Windows — use py launcher or pyenv-win
winget install pyenv-win.pyenv-win
pyenv install 3.12.3
pyenv local 3.12.3
```

### Node.js

```bash
# Check .nvmrc or package.json → "engines": { "node": ">=20" }

# Linux/macOS — use nvm
nvm install           # reads .nvmrc automatically
nvm use

# Windows — use nvm-windows or fnm
winget install Schniz.fnm
fnm use --install-if-missing 20
```

---

## Step 3 — Install the package manager (if not present)

### uv (modern Python — recommended)

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# OR via pip:
pip install uv
# Then add to PATH — see note at bottom
```

### pip (classic Python — always present with Python)
No install needed. Ships with Python.

### Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### npm / pnpm / yarn (Node.js)
`npm` ships with Node.js. For pnpm: `npm install -g pnpm`

---

## Step 4 — Clone and set up the project

```bash
git clone https://github.com/<owner>/<repo>
cd <repo>
```

### Python — uv workspace (has `uv.lock`)

```bash
uv sync --all-packages
# Creates .venv, installs all deps from the lock file exactly.
# Repeat after every `git pull` if uv.lock changed.
```

### Python — uv single package (has `pyproject.toml`, no `uv.lock`)

```bash
uv sync
```

### Python — Poetry (has `poetry.lock`)

```bash
poetry install
poetry shell        # activates the venv
```

### Python — plain pip (has `requirements.txt`)

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell — run once if blocked)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
# If there's also requirements-dev.txt:
pip install -r requirements-dev.txt
```

### Node.js — npm

```bash
npm install         # reads package-lock.json for exact versions
```

### Node.js — pnpm

```bash
pnpm install        # reads pnpm-lock.yaml
```

---

## Step 5 — Configure environment variables

```bash
# Copy the example file — never edit .env.example directly
cp .env.example .env        # Linux/macOS
copy .env.example .env      # Windows CMD
Copy-Item .env.example .env # Windows PowerShell

# Edit .env and fill in required values
# Common ones: API keys, database URLs, service ports
```

> **.env is gitignored** — it lives only on your machine. Never commit it.

---

## Step 6 — Start dependent services (if docker-compose.yml exists)

```bash
docker compose up -d        # starts DB, APIs, etc. in the background
docker compose ps           # verify all services are healthy
docker compose logs -f      # tail logs if something fails
```

Wait for health checks to pass before running the app.

---

## Step 7 — Verify the setup

### Run tests (Python)

```bash
# uv project
uv run pytest -m "not integration" -v

# activated venv / Poetry
pytest -m "not integration" -v
```

### Run tests (Node.js)

```bash
npm test
# or
npm run test:unit
```

### Run the app

```bash
# uv
uv run python src/main.py
uv run <script-name>          # scripts defined in pyproject.toml

# activated venv
python src/main.py

# Node.js
npm run dev
npm start
```

---

## Step 8 — Daily workflow after first setup

```bash
# Pull latest changes
git pull

# Re-sync deps if lock file changed
uv sync --all-packages        # Python/uv
npm install                   # Node.js

# Run
uv run pytest ...
```

---

## Common problems and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `uv: command not found` | uv not on PATH | Add uv's Scripts dir to PATH (see below) |
| `No module named pytest` | Wrong Python / venv not active | Use `uv run pytest` or activate venv first |
| `bad interpreter: No such file` | Committed `.venv` from another machine | Delete `.venv`, run `uv sync` |
| `ModuleNotFoundError` after pull | New dep added, lock file updated | Run `uv sync --all-packages` again |
| `Permission denied: activate.ps1` | PowerShell execution policy | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Port already in use | Previous process still running | `docker compose down` or kill the process |
| `.env` missing | Not copied from `.env.example` | `cp .env.example .env` then fill values |
| `requires-python >=3.12` but have 3.10 | Wrong Python version | Install correct version via pyenv |

---

## Fix uv PATH on Windows (one-time)

After `pip install uv`, uv lands in a Scripts folder not on PATH by default.

```powershell
# Find where uv was installed
Get-ChildItem "C:\Users\$env:USERNAME\AppData\Local\Python" -Recurse -Filter "uv.exe" |
  Select-Object FullName

# Add that Scripts folder to user PATH permanently
$uvScripts = "C:\Users\$env:USERNAME\AppData\Local\Python\pythoncore-3.XX-64\Scripts"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$uvScripts", "User")

# Restart terminal — uv now works directly
uv --version
```

Alternatively, install uv via the official installer (recommended — it sets PATH automatically):

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## What to never commit

```gitignore
.venv/          # always local — recreated by uv sync / pip install
.env            # secrets
__pycache__/
node_modules/   # recreated by npm install
dist/
build/
*.egg-info/
```

## What to always commit

```
uv.lock             # exact Python deps — portable across OS
poetry.lock         # exact deps if using Poetry
package-lock.json   # exact Node deps
pyproject.toml      # dep declarations + project config
.env.example        # template for env vars (no real values)
```
