# Skills & Tools Audit: What's Needed vs. What's Not

An honest accounting of everything loaded into this project and what has actually been required for the end-to-end work done so far (medallion pipeline, semantic model, 4-page report, deployment).

## Summary

Of the ~26 skills, 3 agents, 2 MCP servers, and 5 Python packages bundled into this project, **roughly a third have been essential, another third useful-but-not-critical, and the final third unused.** The project is deliberately broad — it covers Spark, SQL Warehouse, Eventhouse, Tabular Editor, and other workloads we haven't touched. For a lean setup focused purely on Power BI model + report development, you could cut significantly.

---

## MCP Servers

| Server | Used? | How |
|---|---|---|
| **fabric-mcp** (`@microsoft/fabric-mcp`) | **Essential** | Every Fabric API call — listing workspaces, creating/updating semantic models and reports, running notebook jobs, checking deployment status. This is the primary integration point. |
| **PowerBIQuery** (remote, `api.fabric.microsoft.com`) | **Used** | Executing DAX queries against the deployed semantic model to verify data after deployment. Not strictly required for building, but very useful for validation. |

**Verdict:** Both MCP servers earn their keep. fabric-mcp is non-negotiable. PowerBIQuery is valuable for the build-deploy-verify loop.

---

## Python Dependencies

| Package | Used? | How |
|---|---|---|
| **fabric-cicd** | **Used** | Powers `scripts/deploy.py` for deploying PBIP projects to workspaces via REST API. Used as the primary deployment mechanism. |
| **azure-identity** | **Essential** | Authentication for all Azure/Fabric API calls. Required by fabric-cicd and any direct API work. |
| **python-dotenv** | **Essential** | Loads `.env` credentials. Small but necessary. |
| **powerbpy** | **Not used** | Never invoked in any workflow. Was included speculatively. Could be removed. |
| **pbir-utils** | **Not used** | PBIR validation CLI. Mentioned in CLAUDE.md but never actually run — Claude validates structure by reading the skill references directly. Could be useful in CI but hasn't been needed yet. |

**Verdict:** Drop `powerbpy`. Keep `pbir-utils` if you want CI validation later, otherwise remove.

---

## Skill Library 1: powerbi-claude-skills (Lukas Reese)

| Skill | Used? | How |
|---|---|---|
| **pbir-report-builder** | **Essential** | Claude's primary reference for writing PBIR JSON. The JSON templates for cards, charts, tables, slicers, and the field-binding patterns are what Claude consults when creating every visual. Without this, Claude would have to guess at PBIR schema structure. |
| **pbip-dependency-analyzer** | **Not used** | Analyzes PBIP for unused objects. Useful for mature projects with tech debt, but not needed during initial build. |

**Verdict:** pbir-report-builder is the single most important skill for report authoring. The dependency analyzer is dead weight for now.

---

## Skill Library 2: power-bi-agentic-development (data-goblin / Kurt Buhler)

This is the largest library with 15 skills across 6 plugins. Here's what mattered:

### Plugin: pbip (PBIP Project Management)

| Skill | Used? | How |
|---|---|---|
| **pbip** (project structure) | **Essential** | Claude references this to understand PBIP folder layout, file naming, and how `.SemanticModel/` and `.Report/` relate. |
| **tmdl** (TMDL authoring) | **Essential** | Claude's primary reference for writing TMDL files — syntax rules, data types, column definitions, measure syntax, relationship declarations. Used for every table and measure in the semantic model. |
| **pbir-format** (deep PBIR schema) | **Used** | Supplements pbir-report-builder with details on visual formatting objects, conditional formatting, and bookmarks. Not used as heavily as the template-based skill, but consulted for edge cases. |

### Plugin: semantic-models

| Skill | Used? | How |
|---|---|---|
| **standardize-naming-conventions** | **Not used** | Naming conventions reference. Claude followed reasonable naming without consulting this explicitly. |

### Plugin: reports

| Skill | Used? | How |
|---|---|---|
| **pbi-report-design** | **Lightly used** | General design patterns. Claude drew on this implicitly for layout decisions but it wasn't the primary reference. |
| **theme** | **Not used** | Theme editing. We used the default theme. |
| **deneb-visuals** | **Not used** | Deneb/Vega-Lite custom visuals. Not needed for standard Power BI visuals. |
| **svg-visuals** | **Not used** | SVG-based custom visuals. Not needed. |
| **python-visuals** | **Not used** | Python visuals in Power BI. Not needed. |
| **r-visuals** | **Not used** | R visuals in Power BI. Not needed. |

### Plugin: tabular-editor

| Skill | Used? | How |
|---|---|---|
| **te2-cli** | **Not used** | Tabular Editor CLI. We used TMDL directly, not TE. |
| **te-docs** | **Not used** | Tabular Editor documentation. |
| **c-sharp-scripting** | **Not used** | C# scripts for TE. |
| **bpa-rules** | **Not used** | Best Practice Analyzer rules. Useful for model hygiene but not required for building. |

### Plugin: pbi-desktop

| Skill | Used? | How |
|---|---|---|
| **connect-pbid** | **Not used** | Connects to Power BI Desktop TOM via PowerShell. We're on macOS and don't use PBI Desktop for authoring. |

**Verdict:** From 15 skills, only 3 were essential (pbip, tmdl, pbir-format), 1-2 were lightly used (pbi-report-design, pbir-format), and the rest were unused. The unused skills cover Windows-only workflows (PBI Desktop, Tabular Editor), custom visual types (Deneb, SVG, R, Python), and model hygiene tooling (BPA, naming conventions) — all legitimate but not needed for the core build-deploy workflow.

---

## Skill Library 3: skills-for-fabric (Microsoft)

| Skill | Used? | How |
|---|---|---|
| **e2e-medallion-architecture** | **Used** | Reference for the Bronze/Silver/Gold notebook pipeline pattern. Claude consulted this when structuring the data engineering layer. |
| **powerbi-authoring-cli** | **Lightly used** | CLI patterns for creating semantic models via `az rest`. Supplemented the fabric-mcp approach. |
| **powerbi-consumption-cli** | **Not used** | DAX query patterns via CLI. We used the PowerBIQuery MCP server instead. |
| **spark-authoring-cli** | **Not used** | Spark workload management. Notebooks were authored directly in Fabric, not via CLI. |
| **spark-consumption-cli** | **Not used** | Spark data consumption patterns. |
| **sqldw-authoring-cli** | **Not used** | SQL Warehouse creation. Not part of our architecture. |
| **sqldw-consumption-cli** | **Not used** | SQL Warehouse queries. |
| **eventhouse-authoring-cli** | **Not used** | Real-Time Intelligence / KQL Database. Not part of our architecture. |
| **eventhouse-consumption-cli** | **Not used** | KQL queries. |
| **FabricAdmin.agent.md** | **Not used** | Agent for workspace administration. |
| **FabricDataEngineer.agent.md** | **Not used** | Agent for data engineering orchestration. |
| **FabricAppDev.agent.md** | **Not used** | Agent for application development. |

**Verdict:** The medallion architecture skill was genuinely useful. The Power BI authoring CLI was supplementary. Everything else covers workloads (Spark, SQL DW, Eventhouse) and agent patterns we didn't need. The agents are orchestration wrappers — Claude Code already handles orchestration natively through CLAUDE.md.

---

## The Minimal Setup

If you want the leanest possible project that still supports full Power BI model + report development:

### Keep (Essential)

| Component | Why |
|---|---|
| **fabric-mcp** (MCP server) | All Fabric API operations |
| **PowerBIQuery** (MCP server) | DAX query validation |
| **fabric-cicd** + **azure-identity** + **python-dotenv** (Python) | Deployment |
| **scripts/deploy.py** | Deployment automation |
| **pbir-report-builder** skill | PBIR JSON templates and patterns |
| **tmdl** skill | TMDL syntax and rules |
| **pbip** skill | PBIP project structure reference |
| **CLAUDE.md** | Project context and workflow instructions |

### Keep (Recommended)

| Component | Why |
|---|---|
| **pbir-format** skill | Deep PBIR schema details for complex visuals |
| **e2e-medallion-architecture** skill | If you're building data pipelines |
| **pbi-report-design** skill | General report layout guidance |
| **pbir-utils** (Python) | PBIR structure validation (useful in CI) |

### Can Remove

| Component | Why Not Needed |
|---|---|
| **powerbpy** | Never used |
| **pbip-dependency-analyzer** | Model audit tool; not needed during build phase |
| **standardize-naming-conventions** | Nice-to-have reference, not load-bearing |
| **theme, deneb-visuals, svg-visuals, python-visuals, r-visuals** | Custom visual types not used |
| **te2-cli, te-docs, c-sharp-scripting, bpa-rules** | Tabular Editor toolchain; not needed if using TMDL directly |
| **connect-pbid** | Windows + Power BI Desktop only |
| **powerbi-consumption-cli** | Redundant with PowerBIQuery MCP |
| **spark-*-cli, sqldw-*-cli, eventhouse-*-cli** | Workloads not in scope |
| **FabricAdmin, FabricDataEngineer, FabricAppDev agents** | Claude Code handles orchestration natively |
| **powerbi-authoring-cli** | Largely redundant with fabric-mcp |

### Impact of the Minimal Setup

Removing the "Can Remove" items would:
- Cut the `skills/` directory from ~644 files to ~150 files
- Eliminate ~75% of skill content Claude never reads
- Have **zero impact** on the ability to build semantic models, author reports, and deploy to Fabric
- Reduce context noise (Claude occasionally sees irrelevant skills in directory listings)

The trade-off: you lose the ability to handle future requests for Deneb visuals, Tabular Editor scripts, Spark pipelines, or SQL Warehouse work without re-adding those skills.

---

## Recommendation

**Keep everything for now.** The unused skills cost nothing at runtime (Claude only reads them when relevant), and they provide optionality. The only real cost is repo size (~15 MB for the skill libraries) and occasional noise in file listings.

If repo size matters or you want a template others can fork cleanly, extract the "Keep (Essential)" and "Keep (Recommended)" lists above into a minimal starter project and point to the full skill repos as optional add-ons.
