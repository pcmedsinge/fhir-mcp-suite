# fhir-mcp-suite — Demo Runbook

Step-by-step guide for recording the LinkedIn Post #1 demo using MCP Inspector.

---

## Prerequisites

- Docker installed and running
- Node.js ≥ 18 (for `npx`)
- `uv` installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Repo cloned and deps synced:

```bash
cd ~/PracticeApps/MyAIMLProjects2026/fhir-mcp-suite
uv sync --all-packages -q
```

---

## Step 1 — Start the HAPI Validator (required for profile validation)

```bash
docker compose up hapi-validator -d
```

First boot downloads IG packages — **wait ~60 seconds** before using `validate_against_profile`.

Check it's ready:
```bash
curl -s http://localhost:8082/fhir/metadata | grep '"status"'
# expected: "status": "active"
```

---

## Step 2 — Start MCP Inspector

Open a terminal, run:

```bash
cd ~/PracticeApps/MyAIMLProjects2026/fhir-mcp-suite

DANGEROUSLY_OMIT_AUTH=true \
FHIR_BASE_URL=https://hapi.fhir.org/baseR4 \
HAPI_VALIDATOR_URL=http://localhost:8082 \
SMART_ENABLED=false \
  npx @modelcontextprotocol/inspector uv run --package mcp-fhir mcp-fhir
```

Expected output:
```
Starting MCP inspector...
⚙️  Proxy server listening on localhost:6277
⚠️  WARNING: Authentication is disabled.
🚀 MCP Inspector is up and running at:
   http://localhost:6274
```

Open **http://localhost:6274** in your browser, then click **Connect**.

> If you see "Proxy Server PORT IS IN USE", run `pkill -f mcp-inspector` first.

---

## Step 3 — Tool Inputs for the Demo

Once connected, click **Tools** in the left nav. Select each tool and paste the inputs below.

---

### Tool 1 — `fhir_capabilities`

No arguments. Just click **Run Tool**.

Shows: FHIR version, publisher, resource count from the live HAPI server.

---

### Tool 2 — `fhir_search`

```json
{
  "resource_type": "Patient",
  "params": {
    "_count": "3",
    "_sort": "-_lastUpdated"
  }
}
```

Shows: paginated Patient bundle with IDs and names. Note one of the returned patient IDs for the next tool.

---

### Tool 3 — `fhir_read`

```json
{
  "resource_type": "Patient",
  "resource_id": "example"
}
```

> Replace `"example"` with an ID from the `fhir_search` results if you want a live record.

Shows: Full Patient resource from the FHIR server.

---

### Tool 4 — `validate_against_profile` (BROKEN — screenshot for Post #1)

Paste a Patient missing all US Core required fields — validator should return errors.

```json
{
  "resource": {
    "resourceType": "Patient",
    "id": "demo-patient-bad",
    "birthDate": "1985-04-12"
  },
  "profile": "us-core-patient"
}
```

**Expected result:** `"valid": false`, several errors about missing `identifier`, `name.family`, and `gender`.

📸 **Take screenshot here** — this is the "before" shot.

---

### Tool 5 — `validate_against_profile` (FIXED — screenshot for Post #1)

Same patient, now with all required US Core fields added.

```json
{
  "resource": {
    "resourceType": "Patient",
    "id": "demo-patient-good",
    "identifier": [
      {
        "system": "urn:oid:2.16.840.1.113883.4.6",
        "value": "1234567890"
      }
    ],
    "name": [
      {
        "family": "Rivera",
        "given": ["Maria"]
      }
    ],
    "gender": "female",
    "birthDate": "1985-04-12"
  },
  "profile": "us-core-patient"
}
```

**Expected result:** `"valid": true`, zero errors.

📸 **Take screenshot here** — this is the "after" shot.

---

## Step 4 — Targeting a different FHIR server (Epic / Cerner / any)

To run the demo against Epic, Cerner, or any SMART-enabled FHIR server, stop the Inspector
and restart it with the appropriate env vars.

### Public SMART Health IT sandbox (no credentials needed)
```bash
DANGEROUSLY_OMIT_AUTH=true \
FHIR_BASE_URL=https://r4.smarthealthit.org \
SMART_ENABLED=false \
  npx @modelcontextprotocol/inspector uv run --package mcp-fhir mcp-fhir
```

### Epic FHIR sandbox
```bash
DANGEROUSLY_OMIT_AUTH=true \
FHIR_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4 \
SMART_ENABLED=true \
SMART_CLIENT_ID=your-epic-client-id \
SMART_CLIENT_SECRET=your-epic-client-secret \
SMART_SCOPES="system/Patient.read system/Observation.read" \
  npx @modelcontextprotocol/inspector uv run --package mcp-fhir mcp-fhir
```
> `SMART_TOKEN_URL` is optional — auto-discovered from Epic's `.well-known/smart-configuration`.

### Cerner Ignite sandbox
```bash
DANGEROUSLY_OMIT_AUTH=true \
FHIR_BASE_URL=https://fhir-myrecord.cerner.com/r4/<your-tenant-id> \
SMART_ENABLED=true \
SMART_CLIENT_ID=your-cerner-client-id \
SMART_CLIENT_SECRET=your-cerner-client-secret \
SMART_TOKEN_URL=https://authorization.cerner.com/tenants/<tenant-id>/protocols/oauth2/profiles/smart-v1/token \
SMART_SCOPES="system/Patient.read system/Observation.read" \
  npx @modelcontextprotocol/inspector uv run --package mcp-fhir mcp-fhir
```

### Use a `.env` file instead of inline env vars
Copy `.env.example` to `.env`, fill in your credentials, then prefix with `env $(cat .env | xargs)`:
```bash
cp .env.example .env
# edit .env with your credentials
DANGEROUSLY_OMIT_AUTH=true env $(grep -v '^#' .env | xargs) \
  npx @modelcontextprotocol/inspector uv run --package mcp-fhir mcp-fhir
```

For **programmatic usage** (LangGraph, Python agents), see
[`demo/fhir_server_configs.py`](fhir_server_configs.py) which has ready-to-import
`StdioServerParameters` objects for all supported servers.

---

## Step 5 — (Optional) Run the automated demo scripts

These exercise all 5 tools from the command line without a browser:

```bash
# All 5 tools against public HAPI (no Docker needed)
uv run python demo/run_demo.py

# Validation story only (requires validator from Step 1)
uv run python demo/validate_demo.py

# Programmatic client example (all servers)
uv run python demo/fhir_server_configs.py --server hapi
uv run python demo/fhir_server_configs.py --server smart-health
# uv run python demo/fhir_server_configs.py --server epic    # needs credentials
# uv run python demo/fhir_server_configs.py --server cerner  # needs credentials
```

---

## Tear Down

```bash
# Stop MCP Inspector: Ctrl+C in its terminal
# Stop HAPI validator:
docker compose down hapi-validator
```

---

## Port Reference

| Service         | Port                          |
|-----------------|-------------------------------|
| MCP Inspector UI | http://localhost:6274        |
| Inspector proxy  | localhost:6277               |
| HAPI Validator   | http://localhost:8082        |
| HAPI FHIR server (optional) | http://localhost:8081 |
