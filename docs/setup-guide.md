# Setting Up Claude Code as Your Power BI Developer Bot

A step-by-step guide to reproducing this environment from scratch.

## Executive Summary

This project turns Claude Code into a Power BI developer that can build end-to-end data pipelines, semantic models, and reports — all from the command line, with no drag-and-drop required. It works by combining three things:

1. **Text-based Power BI formats** (TMDL for models, PBIR for reports) that Claude can read and write like any source code
2. **MCP servers** that give Claude live access to the Fabric REST API and DAX query engine
3. **Skill libraries** (community + Microsoft) that teach Claude the TMDL/PBIR schemas, design patterns, and deployment workflows

The result: you describe what you want in natural language, Claude writes the model definitions and report JSON, and deploys them to Power BI Service via API. The entire Power BI project is version-controlled in Git with meaningful diffs.

**What we've built so far with this setup:**
- A medallion data pipeline (Bronze/Silver/Gold) across 4 Fabric notebooks and 3 lakehouses, ingesting from PostgreSQL
- A 12-table semantic model with DAX measures and TCMB exchange rate integration
- A 4-page report (Executive Summary, Bills & Vendors, Payments, Currency & FX) with 19+ visuals
- Automated deployment via Fabric REST API

All of it was authored by Claude Code working in this repo.

## Requirements

### Must Have

| Requirement | Version / Details |
|---|---|
| **Claude Code** | CLI, Desktop app, or IDE extension (any works) |
| **Python** | 3.10+ |
| **uv** | Python package manager (replaces pip) |
| **Node.js** | 18+ (needed to run the Fabric MCP server via `npx`) |
| **Azure Entra ID app registration** | Service principal for API access |
| **Power BI Pro or PPU license** | Required for all API operations |
| **Fabric capacity** | Trial works for API deployment; paid (F2+) needed for Git sync |

### Nice to Have

| Requirement | Purpose |
|---|---|
| Power BI Desktop (Windows) | Creating initial PBIP boilerplate; not needed if using API/web authoring |
| Azure CLI (`az`) | Used by some Fabric skills for `az rest` commands |
| Tabular Editor | Advanced C# scripting and Best Practice Analyzer |

## Step-by-Step Setup

### Step 1: Create the Project Repo

Create a new Git repo with this structure:

```
your-project/
├── CLAUDE.md              # Instructions Claude reads on startup
├── .mcp.json              # MCP server registrations
├── pyproject.toml         # Python dependencies
├── .env.example           # Credential template
├── .gitignore
├── projects/              # PBIP projects go here
├── scripts/
│   └── deploy.py          # Deployment script
├── skills/                # Skill libraries (cloned in Step 3)
└── docs/
    └── azure-setup.md     # Azure credentials guide
```

### Step 2: Install Python Dependencies

Create a `pyproject.toml`:

```toml
[project]
name = "your-pbi-project"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fabric-cicd>=0.1.0",
    "azure-identity>=1.15.0",
    "python-dotenv>=1.0.0",
]
```

Then install:

```bash
uv sync
```

`fabric-cicd` is the key dependency — it's Microsoft's library for deploying PBIP projects to Fabric workspaces via the REST API.

### Step 3: Clone the Skill Libraries

These are the reference materials Claude reads to understand Power BI file formats:

```bash
mkdir -p skills

# PBIR report builder + dependency analyzer (Lukas Reese)
git clone https://github.com/lukasreese/powerbi-claude-skills.git skills/powerbi-claude-skills

# TMDL, PBIR schemas, themes, design patterns (data-goblin / Kurt Buhler)
git clone https://github.com/data-goblin/power-bi-agentic-development.git skills/power-bi-agentic-development

# Microsoft's official Fabric skills (medallion architecture, CLI patterns)
git clone https://github.com/microsoft/skills-for-fabric.git skills/skills-for-fabric
```

After cloning, remove the `.git` directories so they're tracked as part of your repo:

```bash
rm -rf skills/powerbi-claude-skills/.git
rm -rf skills/power-bi-agentic-development/.git
rm -rf skills/skills-for-fabric/.git
```

**What each library contributes** (see the companion doc `docs/skills-audit.md` for a detailed breakdown of what's been needed vs. not):

| Library | What Claude uses it for |
|---|---|
| **powerbi-claude-skills** | PBIR JSON templates for visuals (cards, charts, tables, slicers), page layout patterns |
| **power-bi-agentic-development** | TMDL syntax and rules, PBIR schema details, PBIP structure reference |
| **skills-for-fabric** | Medallion architecture patterns, Fabric REST API patterns |

### Step 4: Register MCP Servers

Create `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "fabric-mcp": {
      "command": "npx",
      "args": ["-y", "@microsoft/fabric-mcp@latest", "server", "start", "--mode", "all"]
    },
    "PowerBIQuery": {
      "type": "http",
      "url": "https://api.fabric.microsoft.com/v1/mcp/powerbi",
      "headers": {},
      "tools": ["ExecuteQuery"],
      "oauthClientId": "aebc6443-996d-45c2-90f0-388ff96faa56",
      "oauthPublicClient": true
    }
  }
}
```

**What these do:**

- **fabric-mcp** (`@microsoft/fabric-mcp`) — runs locally via npx. Gives Claude tools to list workspaces, create/update items, manage Git integration, run notebook jobs, etc. This is the primary workhorse for all Fabric API operations.
- **PowerBIQuery** — Microsoft's remote MCP endpoint. Lets Claude execute DAX queries against deployed semantic models. Uses OAuth device code flow for auth.

When Claude Code starts in this directory, it auto-discovers `.mcp.json` and starts these servers.

### Step 5: Set Up Azure Credentials

Follow `docs/azure-setup.md` for the full walkthrough. The abbreviated version:

1. Register an app in [Microsoft Entra ID](https://entra.microsoft.com)
2. Create a client secret
3. Add Power BI API permissions: `Dataset.ReadWrite.All`, `Workspace.ReadWrite.All`, `Report.ReadWrite.All`, `Content.Create`
4. Grant admin consent
5. Create a security group containing the app
6. Enable service principals in Power BI Admin Portal tenant settings
7. Add the service principal to your target workspace(s) with Member or Admin role

Then create `.env`:

```
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-client-id>
AZURE_CLIENT_SECRET=<your-client-secret>
POWERBI_WORKSPACE_ID=<your-workspace-id>
```

### Step 6: Write the CLAUDE.md

This is the most important file — it's what Claude reads on every conversation start. It should contain:

1. **Current deployment state** — what's already deployed, workspace IDs, known issues
2. **Architecture overview** — how the pieces fit together
3. **File format reference** — PBIP, PBIR, TMDL basics
4. **Workflow instructions** — how to create/edit/deploy content
5. **Available MCP servers** — what tools Claude has access to
6. **Available skills** — what reference material exists and where to find it
7. **Environment variables** — what credentials are configured

See the `CLAUDE.md` in this repo for a working example. Key points:

- Be explicit about what's deployed and what's not
- Document known issues and workarounds (e.g., "DirectLake didn't work, use Import mode")
- Point Claude to specific skill files by path when relevant
- Keep it updated as the project evolves

### Step 7: Add the Deploy Script

Copy `scripts/deploy.py` from this repo. It wraps `fabric-cicd` to deploy PBIP projects:

```bash
# Deploy semantic model + report to a workspace
uv run python scripts/deploy.py \
  --project projects/YourProject \
  --workspace-id <workspace-guid>
```

The script supports three auth methods:
- **Service principal via env vars** (default if `AZURE_CLIENT_SECRET` is set)
- **Azure CLI** (`--spn-auth`)
- **Interactive browser** (fallback)

### Step 8: Create Initial PBIP Boilerplate

Claude cannot create a PBIP project from scratch — Power BI Desktop generates version-specific boilerplate files (`report.json`, `.platform`, `version.json`, themes) that can't be reliably hand-written.

Options:
1. **Power BI Desktop** (Windows) — create a blank report connected to your data source, save as PBIP format
2. **Power BI web authoring** (app.powerbi.com) — create in the browser, then download via API
3. **Fabric REST API** — use the fabric-mcp tools to create a blank item and download its definition

For the EnS Finance project, we used the Fabric REST API (option 3) — Claude created the semantic model and report definitions directly via API, then worked with them as local TMDL/PBIR files.

### Step 9: Start Building

Open Claude Code from the project root:

```bash
claude
```

Claude will auto-load `CLAUDE.md`, start MCP servers, and have access to all skills. You can now ask it to:

- "Create a semantic model with these tables and relationships"
- "Add a KPI dashboard page with revenue cards and a trend chart"
- "Write DAX measures for year-over-year growth"
- "Deploy the semantic model to the workspace"
- "Run a DAX query to check if the data looks right"

## How It Works End-to-End

```
You describe what you want
        │
        ▼
Claude reads TMDL/PBIR skills for schema knowledge
        │
        ▼
Claude writes .tmdl files (tables, measures, relationships)
Claude writes .json files (pages, visuals, page order)
        │
        ▼
Claude deploys via Fabric REST API (or you run deploy.py)
        │
        ▼
Report appears in Power BI Service
        │
        ▼
You review, ask for changes, iterate
```

## Gotchas and Lessons Learned

1. **DirectLake mode didn't work** — OneLake permission issues with service principals. Import mode via Lakehouse SQL endpoint works reliably.

2. **OAuth2 credentials need rebinding** — after redeploying a semantic model via API, you must manually re-bind data source credentials in Power BI Service (Settings > Data source credentials). There's no API for this yet.

3. **Fabric Git sync needs paid capacity** — GitHub Git integration requires F2 SKU or higher. On a trial, use `deploy.py` instead.

4. **PBIP boilerplate is version-sensitive** — the `report.json`, `version.json`, and theme files generated by Power BI Desktop contain version-specific schemas. Don't try to create them by hand.

5. **TCMB URL format is fiddly** — the Central Bank of Turkey API uses `YYYYMM/DDMMYYYY.xml` (4-digit year in the filename, 2-digit year not valid). Claude got this wrong initially and we had to correct it.

6. **Semantic model deployment is async** — the Fabric REST API returns 202 with a `Location` header. You must poll that URL until the operation shows `Succeeded`. Claude handles this via the fabric-mcp tools.

7. **Keep CLAUDE.md current** — this is the single most important file for Claude's effectiveness. If it's out of date, Claude will make wrong assumptions about what's deployed.
