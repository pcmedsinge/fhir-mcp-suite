# MCP Server Deployment Models

> Reference guide covering the two ways to deploy an MCP server, when to use each,
> and what platforms/registries support each model.
> Written from experience with `fhir-mcp-suite` (June 2026).

---

## The Two Models

### Model 1 — Local / stdio

The server runs as a **subprocess on the user's own machine**. The MCP client
(Claude Desktop, Cursor, etc.) launches it directly.

```
User's machine
┌─────────────────────────────────────────────────────┐
│  Claude Desktop                                      │
│       │  spawns subprocess                           │
│       ▼                                              │
│  uvx mcp-fhir   ──► https://hapi.fhir.org/baseR4   │
│  (runs locally)     (external API, internet)         │
└─────────────────────────────────────────────────────┘
```

**How the user connects:**

```json
{
  "mcpServers": {
    "fhir": {
      "command": "uvx",
      "args": ["mcp-fhir"],
      "env": { "FHIR_BASE_URL": "https://hapi.fhir.org/baseR4" }
    }
  }
}
```

**Characteristics:**

| Property | Value |
|----------|-------|
| Hosting cost | None |
| Infrastructure | None — runs on user's machine |
| Install required | Yes — `pip install` or `uvx` |
| Public URL | None |
| Latency | Near-zero (local process) |
| Auth | Each user configures their own credentials |
| Scalability | N/A — one instance per user |
| Best for | Developer tools, open-source, privacy-sensitive data |

---

### Model 2 — Remote / hosted (SSE or Streamable HTTP)

The server runs on **your infrastructure** (cloud VM, container, serverless).
The MCP client connects to it via HTTPS.

```
User's machine                   Your cloud server
┌───────────────┐   HTTPS/SSE    ┌──────────────────────────┐
│ Claude Desktop│ ─────────────► │ https://api.you.com/mcp  │
│               │                │   mcp-fhir (SSE mode)    │
└───────────────┘                │       │                  │
                                 │       ▼                  │
                                 │ https://your-fhir-server │
                                 └──────────────────────────┘
```

**How the user connects:**

```json
{
  "mcpServers": {
    "fhir": {
      "url": "https://api.yourcompany.com/mcp"
    }
  }
}
```

**Characteristics:**

| Property | Value |
|----------|-------|
| Hosting cost | Yes — cloud VM/container/serverless |
| Infrastructure | You manage (or use managed platforms) |
| Install required | No — user just adds a URL |
| Public URL | Required (HTTPS) |
| Latency | Network round-trip (10–200ms typical) |
| Auth | You control — OAuth, API keys, etc. |
| Scalability | You scale horizontally |
| Best for | SaaS products, enterprise, non-technical users |

---

## Your current servers (`fhir-mcp-suite`)

All three servers are built for **Model 1 (local/stdio)**:

```bash
uvx mcp-fhir            # runs locally, no hosting needed
uvx mcp-terminology
uvx mcp-clinical-reasoner
```

They can also run in SSE mode (`MCP_TRANSPORT=sse`) if you want to host them,
but that requires you to deploy and maintain cloud infrastructure.

---

## Which model to choose — decision guide

```
Are you building a commercial SaaS / enterprise product?
  YES → Model 2 (Remote/hosted)
  NO  ↓

Do your users need to install anything?
  They can't / won't install → Model 2 (Remote/hosted)
  They're developers / technical → Model 1 (Local/stdio) ✅

Does your server handle sensitive PHI that must stay on the user's machine?
  YES → Model 1 (Local/stdio) — data never leaves their machine
  NO  ↓

Do you need centralised usage tracking / billing per user?
  YES → Model 2 (Remote/hosted)
  NO  → Model 1 (Local/stdio) ✅

Do you want zero hosting cost?
  YES → Model 1 (Local/stdio) ✅
```

**For `fhir-mcp-suite`**: Model 1 is correct. Target users are healthcare AI
developers and engineers — they are comfortable with `uvx install`, and the
servers call public APIs (no PHI), so there's no privacy reason to force remote hosting.

---

## Platform / registry compatibility

| Platform | Model 1 (stdio) | Model 2 (remote) | Notes |
|----------|----------------|-----------------|-------|
| **PyPI** | ✅ Primary | ✅ Also fine | Distributes the package |
| **MCP Registry** (registry.modelcontextprotocol.io) | ✅ Supported | ✅ Supported | Supports both via `server.json` |
| **Smithery** (smithery.ai) | ❌ Not supported | ✅ Required | Needs a live HTTP URL |
| **Glama** (glama.ai/mcp/servers) | ✅ Supported | ✅ Supported | Accepts GitHub/PyPI links |
| **Claude Desktop config** | ✅ command + args | ✅ url field | Different config format per model |
| **Docker Hub** | ✅ Package container | ✅ Deploy container | Can serve either model |

---

## Converting Model 1 → Model 2 (if needed in future)

Your servers already support SSE transport. To host them remotely:

### Step 1 — Choose a hosting platform

| Platform | Free tier | Notes |
|----------|-----------|-------|
| Railway | 5 USD/month after trial | Easiest — `railway up` |
| Render | Free (with sleep) | Good for demos |
| Fly.io | Generous free tier | Best for always-on |
| AWS ECS / Cloud Run | Pay-per-use | For production scale |

### Step 2 — Build and push Docker image

Each package already has a `Dockerfile`. Example for `mcp-fhir`:

```bash
cd packages/mcp-fhir
docker build -t mcp-fhir .
docker tag mcp-fhir yourregistry/mcp-fhir:latest
docker push yourregistry/mcp-fhir:latest
```

### Step 3 — Set environment variable for SSE transport

```bash
MCP_TRANSPORT=sse
MCP_HOST=0.0.0.0
MCP_PORT=8000
FHIR_BASE_URL=https://your-fhir-server/fhir
```

### Step 4 — Deploy and get a public URL

```
https://mcp-fhir.railway.app/sse   ← example
```

### Step 5 — List on Smithery

With a live URL, you can now submit to https://smithery.ai using the
"Publish an MCP Server" form:
- **Namespace / Server ID**: `pcmedsinge/mcp-fhir`
- **MCP Server URL**: `https://mcp-fhir.railway.app/sse`

---

## Summary

| Question | Answer |
|----------|--------|
| What model does `fhir-mcp-suite` use? | Model 1 — local/stdio |
| How do users install it? | `uvx mcp-fhir` (no server to host) |
| Why can't it list on Smithery? | Smithery requires a hosted HTTP URL |
| Can it be converted to Model 2? | Yes — SSE transport is already built in |
| Should you convert it now? | No — adds cost and complexity without benefit for current audience |
| When should you consider Model 2? | When building a commercial product or targeting non-technical users |
