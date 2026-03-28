# Power BI + Fabric Development with Claude Code

This project enables Claude to build Power BI dataflows, semantic models, and reports using modern text-based formats (PBIR, TMDL, PBIP) and deploy them to Fabric/Power BI Service.

## Current Deployment

**Workspace:** E&S Bilgi AI Dev (`c44d2ba3-a7ca-4d33-a7ef-8d2080dceefa`)

| Item | Type | Notes |
|---|---|---|
| Bronze_EnSFinance | Notebook + Lakehouse | Ingests 7 tables from Neon PostgreSQL |
| Silver_EnSFinance | Notebook + Lakehouse | Cleans/normalizes, Boyut vendor normalization |
| Gold_EnSFinance | Notebook + Lakehouse | Star schema: 8 dims + 3 facts (receipt missing — needs more source data) |
| TCMB_ExchangeRates | Notebook | Fetches 1 year of USD/TRY + EUR/TRY from TCMB REST API into Gold |
| EnS Finance | SemanticModel | Import mode via Lakehouse SQL endpoint, 12 tables, DAX measures with TCMB FX conversion |
| EnS Finance Report | Report | 4 pages: Executive Summary, Bills & Vendors, Payments, Currency & FX |

**Pipeline order:** Bronze → Silver → Gold + TCMB (parallel) → Refresh semantic model

**Known issues:**
- `receipt` table not in Gold (only 1 source row; re-run Gold notebook when more data exists)
- After redeploying semantic model via API, OAuth2 credentials must be re-bound in Settings > Data source credentials
- DirectLake mode didn't work (OneLake permission issues); using Import mode via SQL endpoint instead
- TCMB URL format: `https://www.tcmb.gov.tr/kurlar/YYYYMM/DDMMYYYY.xml` (4-digit year, not 2-digit)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  Claude Code                                            │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Fabric MCP    │  │ Skills       │  │ fabric-cicd  │ │
│  │ (workspaces,  │  │ (PBIR report │  │ (deploy PBIP │ │
│  │  items, Git)  │  │  builder,    │  │  to workspace│ │
│  │               │  │  TMDL, etc.) │  │  via API)    │ │
│  └───────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
└──────────┼─────────────────┼─────────────────┼──────────┘
           │                 │                 │
           ▼                 ▼                 ▼
    Fabric REST API    Local PBIP files    Fabric REST API
                       (Git-tracked)
```

## File Formats

- **PBIP** — Power BI Project folder. Contains a `.Report/` and `.SemanticModel/` subfolder.
- **PBIR** — Enhanced Report Format. JSON files for each page, visual, bookmark. Located in `.Report/definition/`.
- **TMDL** — Tabular Model Definition Language. Text files for tables, measures, relationships. Located in `.SemanticModel/definition/`.

## Workflow: Creating Power BI Content

### Step 1: Create Initial PBIP Project (User Action)

**IMPORTANT: Do NOT create a PBIP project from scratch.** Power BI Desktop generates boilerplate files (`report.json`, `.platform`, `version.json`, themes) with version-specific schemas and GUIDs that cannot be reliably replicated.

The user must:
1. Open Power BI Desktop (Windows) or Power BI web authoring
2. Connect to the data source
3. Save as PBIP format (File > Save as > Power BI Project)
4. Place the PBIP folder in `projects/` directory

Alternatively, use the Fabric REST API to create items and download their definitions.

### Step 2: Add/Edit Semantic Model (Claude)

Use the **TMDL skill** or **Power BI Modeling MCP** to:
- Add tables with columns and data types
- Write DAX measures
- Define relationships between tables
- Set up calculation groups, hierarchies, RLS roles

TMDL files go in `projects/<name>.SemanticModel/definition/`:
```
definition/
├── database.tmdl          # compatibilityLevel
├── model.tmdl             # model-level settings
├── tables/
│   ├── Sales.tmdl         # table with columns + measures
│   └── Calendar.tmdl      # date table
├── relationships.tmdl     # all relationships
└── roles/                 # RLS roles
```

Reference: `skills/power-bi-agentic-development/plugins/pbip/skills/tmdl/SKILL.md`

### Step 3: Add Report Pages & Visuals (Claude)

Use the **PBIR Report Builder skill** to write PBIR JSON files:
- Create page folders in `projects/<name>.Report/definition/pages/`
- Add `page.json` for each page
- Add `visual.json` for each visual in `visuals/` subfolder
- Update `pages.json` to register new pages in the page order

Reference: `skills/powerbi-claude-skills/pbir-report-builder/SKILL.md`
Templates: `skills/powerbi-claude-skills/pbir-report-builder/references/json-templates/`

### Step 4: Validate

Use `pbir-utils` CLI to validate PBIR structure:
```bash
uv run pbir-utils validate projects/<name>.Report/
```

### Step 5: Deploy

Option A — **Fabric REST API** (direct deployment, used for EnS Finance):
```python
# Create: POST /v1/workspaces/{ws}/semanticModels with TMDL parts
# Update: POST /v1/workspaces/{ws}/semanticModels/{id}/updateDefinition
# Report: POST /v1/workspaces/{ws}/reports with PBIR parts
# All operations are async (202) — poll the Location header URL until Succeeded
```

Required parts for semantic model: `definition.pbism` + `definition/*.tmdl` + `definition/tables/*.tmdl`
Required parts for report: `definition.pbir` + `definition/version.json` + `definition/report.json` + `definition/pages/pages.json` + page/visual JSON files

Option B — **fabric-cicd** (API deployment):
```bash
uv run python scripts/deploy.py --project projects/<name> --workspace <workspace-id>
```

Option C — **Git integration** (commit-based deployment, requires paid Fabric capacity):
```bash
git add projects/<name>
git commit -m "Add <name> report"
git push
# Fabric Git sync picks up changes automatically
```

**Note:** GitHub Git sync requires paid Fabric capacity (F2+). On a trial, use Option A or B. See `docs/azure-setup.md` Step 8 for details.

## Available MCP Servers

### Fabric MCP Server (`@microsoft/fabric-mcp`)
Registered in `.mcp.json`. Provides access to Fabric REST APIs:
- List/create/manage workspaces
- List/create/manage items (semantic models, reports, dataflows, etc.)
- Git integration operations
- Job execution (refreshes, notebook runs)

### Remote Power BI MCP (if enabled by admin)
URL: `https://api.fabric.microsoft.com/v1/mcp/powerbi`
- Execute DAX queries against deployed semantic models
- Get model schemas
- Natural language to DAX

## Available Skills

### From `skills/powerbi-claude-skills/`
- **pbir-report-builder** — Generate PBIR JSON pages and visuals. Has JSON templates for cards, charts, tables, slicers, IBCS visuals.

### From `skills/power-bi-agentic-development/`
- **pbip** — PBIP project management, file types, rename cascading
- **pbir-format** — Deep PBIR schema reference, visual JSON patterns, formatting objects, bookmarks, conditional formatting
- **tmdl** — TMDL authoring, syntax rules, best practices
- **pbi-report-design** — Report design patterns
- **theme** — Power BI theme editing
- **deneb-visuals** — Deneb/Vega-Lite custom visuals
- **svg-visuals** — SVG-based visuals
- **standardize-naming-conventions** — Naming conventions for semantic models
- **bpa-rules** — Best Practice Analyzer rules for Tabular Editor
- **c-sharp-scripting** — C# scripts for Tabular Editor

### From `skills/skills-for-fabric/`
- **powerbi-authoring-cli** — Create/manage semantic models via `az rest` CLI and Fabric API
- **powerbi-consumption-cli** — DAX queries and metadata discovery
- **spark-authoring-cli** / **spark-consumption-cli** — Spark workload management
- **sqldw-authoring-cli** / **sqldw-consumption-cli** — SQL warehouse operations
- **eventhouse-authoring-cli** / **eventhouse-consumption-cli** — Real-Time Intelligence
- **e2e-medallion-architecture** — End-to-end medallion data architecture

## Key References

- PBIR JSON schemas: `skills/powerbi-claude-skills/pbir-report-builder/references/json-schemas/`
- Visual type identifiers: `skills/powerbi-claude-skills/pbir-report-builder/references/visual-types.md`
- Field binding patterns: `skills/powerbi-claude-skills/pbir-report-builder/references/field-references.md`
- TMDL syntax & best practices: `skills/power-bi-agentic-development/plugins/pbip/skills/tmdl/SKILL.md`
- PBIR structure reference: `skills/power-bi-agentic-development/plugins/pbip/skills/pbir-format/SKILL.md`
- Fabric CLI authentication: `skills/skills-for-fabric/CLAUDE.md`

## Environment Variables

```
AZURE_TENANT_ID      — Azure Entra ID tenant
AZURE_CLIENT_ID      — App registration client ID
AZURE_CLIENT_SECRET  — App registration secret
POWERBI_WORKSPACE_ID — Default workspace ID
```

See `docs/azure-setup.md` for setup instructions.

## macOS Note

Power BI Desktop is Windows-only. On macOS, create initial PBIP projects via:
1. Power BI web authoring in the browser (app.powerbi.com)
2. Fabric REST API to create items and download definitions
3. The `powerbi-authoring-cli` skill (uses `az rest`)
4. A Windows VM or remote machine

Claude can then add pages, visuals, and measures to the downloaded PBIP structure.
