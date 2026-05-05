# Installing mcp-fhir with Claude Desktop

`mcp-fhir` is a [Model Context Protocol](https://modelcontextprotocol.io) server that
gives Claude direct access to any FHIR R4 server — read resources, search, and validate
against US Core / IPS profiles.

---

## Quick install (recommended)

### Prerequisites

- Python 3.12+ on your PATH
- [`uv`](https://docs.astral.sh/uv/) — `curl -Lsf https://astral.sh/uv/install.sh | sh`
- Claude Desktop (macOS or Windows)

### Step 1 — Verify the server works (no config needed)

```bash
uvx mcp-fhir --help
```

You should see:

```
usage: mcp-fhir [-h] [--transport {stdio,sse}] ...
```

### Step 2 — Add to Claude Desktop config

Open `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows) and add
the `mcp-fhir` entry to the `mcpServers` object:

```json
{
  "mcpServers": {
    "mcp-fhir": {
      "command": "uvx",
      "args": ["mcp-fhir"],
      "env": {
        "FHIR_BASE_URL": "https://hapi.fhir.org/baseR4",
        "HAPI_VALIDATOR_URL": "http://localhost:8082",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

> **Tip:** To use a local or organisation FHIR server, change `FHIR_BASE_URL` to
> your server's base URL (e.g. `http://localhost:8081/fhir`).

### Step 3 — Restart Claude Desktop

Quit and relaunch Claude Desktop. You should see **mcp-fhir** listed in the
tools panel (hammer icon).

---

## Running the HAPI validator sidecar (optional but recommended)

The `validate_against_profile` tool requires a locally running HAPI validator
instance. Start it with Docker:

```bash
docker run -d --name hapi-validator \
  -p 8082:8080 \
  markiantorno/validator-wrapper:latest
```

Or use the included Compose file (also starts a local HAPI FHIR server):

```bash
git clone https://github.com/pcmedsinge/fhir-mcp-suite
cd fhir-mcp-suite
docker compose up hapi-validator hapi-fhir -d
```

---

## Example Claude prompts

Once installed, try these prompts in Claude Desktop:

```
Show me what resource types the FHIR server supports.

Read the Patient resource with id "example".

Search for the last 5 Observations.

Validate this Patient resource against the US Core Patient profile:
{"resourceType":"Patient","id":"test","identifier":[{"value":"123"}],"name":[{"family":"Doe"}],"gender":"male"}
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `FHIR_BASE_URL` | `https://hapi.fhir.org/baseR4` | FHIR R4 base URL |
| `HAPI_VALIDATOR_URL` | `http://localhost:8080` | HAPI validator sidecar |
| `FHIR_TIMEOUT_S` | `30` | HTTP timeout (seconds) |
| `FHIR_MAX_RESULTS` | `20` | Default `_count` for searches |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | `json` | `json` (prod) or `console` (dev) |
| `LANGFUSE_PUBLIC_KEY` | — | LangFuse observability (optional) |
| `LANGFUSE_SECRET_KEY` | — | LangFuse observability (optional) |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Self-hosted LangFuse URL |

---

## Upgrading

```bash
uvx mcp-fhir@latest --help   # check latest version
```

Update the `args` in your Claude Desktop config to pin a specific version:

```json
"args": ["mcp-fhir==1.0.0"]
```

---

## Troubleshooting

**Claude doesn't show the mcp-fhir tools**
: Check that `uvx mcp-fhir` runs without errors in your terminal.
  Restart Claude Desktop after editing the config file.

**`validate_against_profile` returns a connection error**
: The HAPI validator sidecar is not running. Start it with `docker run` or
  `docker compose up hapi-validator`.

**`fhir_search_next` raises "does not match configured FHIR server"**
: The pagination URL returned by your FHIR server uses a different host than
  `FHIR_BASE_URL`. Update `FHIR_BASE_URL` to match the actual server host.
