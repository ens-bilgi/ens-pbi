# Partner Briefing: Claude Code as Power BI Developer

Supplementary documentation covering what the setup guide and skills audit don't: capability evidence, known limitations, security posture, scalability outlook, and competitive positioning.

---

## 1. What Claude Actually Built (Capability Evidence)

We can't replay past conversations, but the Git history and project files tell the full story. Everything below was authored by Claude Code across a handful of conversations, with human review and iteration.

### The Data Pipeline (Fabric Notebooks + Lakehouses)

Claude authored 4 Fabric notebooks and configured 3 lakehouses, deployed via the Fabric REST API:

| Notebook | What It Does |
|---|---|
| **Bronze_EnSFinance** | Connects to Neon PostgreSQL (external source), ingests 7 raw tables into Bronze Lakehouse |
| **Silver_EnSFinance** | Cleans and normalizes data, including Boyut vendor name standardization; writes to Silver Lakehouse |
| **Gold_EnSFinance** | Builds star schema: 8 dimension tables + 3 fact tables (Bill, Invoice, Payment); writes to Gold Lakehouse |
| **TCMB_ExchangeRates** | Fetches 1 year of USD/TRY and EUR/TRY daily rates from the Central Bank of Turkey REST API, writes to Gold |

Pipeline order: Bronze -> Silver -> Gold + TCMB (parallel) -> Refresh semantic model.

### The Semantic Model (12 Tables, TMDL)

Claude wrote all TMDL definitions from scratch — 12 table files, a relationships file, and model configuration. Highlights:

**Star schema design:**
- 8 dimension tables: Date, Vendor, Client, Currency, Payment Method, Expense Category, User, Transaction Status
- 3 fact tables: Bill, Invoice, Payment (Receipt excluded — only 1 row in source data)
- 1 reference table: Exchange Rate (TCMB daily FX data)
- 11 relationships connecting facts to dimensions via surrogate keys

**DAX measures with FX conversion:**
- Basic aggregations: `Total Bills`, `Total Invoices`, `Total Payments`
- Multi-currency conversion: `Total Bills TRY` uses `SUMX` + `LOOKUPVALUE` to convert each bill to Turkish Lira via the TCMB selling rate for that bill's date and currency
- Time intelligence: `YTD Bills TRY` using `TOTALYTD`
- Status-filtered counts: `Outstanding Bills`, `Outstanding Invoices`
- Coverage metrics: payment coverage ratios

**Model configuration:**
- `culture: tr-TR` (Turkish locale)
- `discourageImplicitMeasures` (best practice for semantic models)
- Parameterized connection: `SqlEndpoint` and `Database` as M parameters pointing to the Gold Lakehouse SQL endpoint

### The Report (4 Pages, 19+ Visuals, PBIR JSON)

Claude generated all PBIR JSON files — page definitions, visual configurations, and field bindings:

| Page | Visuals | Purpose |
|---|---|---|
| **Executive Summary** | 4 KPI cards (Total Bills, Total Payments, Outstanding, VAT) + trend chart + recent transactions table | At-a-glance financial overview |
| **Bills & Vendors** | Bills detail table + bar chart by vendor + pie chart by status | Vendor spend analysis |
| **Payments** | Payments detail table + bar chart by payment method + coverage card | Payment tracking |
| **Currency & FX** | Exchange rates table + USD/TRY line chart + EUR/TRY line chart | FX monitoring |

### Deployment (REST API)

Claude deployed both the semantic model and report to the `E&S Bilgi AI Dev` workspace using the Fabric REST API:
- Created items via `POST /v1/workspaces/{ws}/semanticModels` and `/reports`
- Updated definitions via `POST .../updateDefinition` with base64-encoded TMDL/PBIR parts
- Handled async 202 responses by polling the `Location` URL until `Succeeded`
- Also wrote `scripts/deploy_api.py` — a standalone deployment script for direct REST API calls (separate from the `fabric-cicd`-based `deploy.py`)

### Bug Fixes and Iteration

The FX line charts on the Currency page were initially empty. Root cause: the visuals referenced `forex_selling` as a raw column, but the model uses `discourageImplicitMeasures` and the column had `summarizeBy: none`. Charts need aggregated values. Claude diagnosed this, created a `Selling Rate` measure, and updated both visuals — a 4-file fix captured in commit `88df724`.

This is a good example of the kind of iteration that's typical: Claude builds it, you review in Power BI Service, report what's wrong, Claude diagnoses and fixes.

---

## 2. What Claude Can't Do (Limitations)

Be upfront about these with clients:

### Hard Limitations

| Limitation | Detail |
|---|---|
| **Can't create PBIP boilerplate** | Power BI Desktop generates `report.json`, `.platform`, `version.json`, and theme files with version-specific schemas and GUIDs. Claude cannot reliably produce these from scratch. A human (or API call) must create the initial scaffold. |
| **Can't bind OAuth2 credentials** | After deploying a semantic model via API, data source credentials must be manually re-bound in Power BI Service (Settings > Data source credentials). No API exists for this yet. |
| **No visual preview during authoring** | Claude writes PBIR JSON "blind" — there's no way to render the report locally. You must deploy and check in the browser. |
| **Can't use Power BI Desktop** | PBI Desktop is Windows-only and has no CLI. Claude can't open it, connect to it, or interact with it on macOS/Linux. (The Modeling MCP Server changes this partially, but requires a running PBI Desktop instance on Windows.) |
| **Can't do drag-and-drop design** | Pixel-perfect visual positioning, precise chart styling, and layout polishing are much harder via JSON than in the GUI. Expect to do final cosmetic tweaks manually. |

### Soft Limitations (Works, But Imperfectly)

| Limitation | Detail |
|---|---|
| **Complex DAX** | Claude writes solid basic-to-intermediate DAX (aggregations, time intelligence, LOOKUPVALUE, CALCULATE with filters). Very complex filter context scenarios, dynamic security, or advanced calculation groups may need human review. Community reports ~85-90% first-try success for DAX. |
| **PBIR edge cases** | Standard visuals (cards, bar charts, tables, line charts, pie charts) work reliably. Exotic formatting, mobile layouts, interaction configs, and custom visuals are more error-prone. |
| **TMDL whitespace sensitivity** | TMDL uses indentation-based syntax. Claude occasionally produces formatting errors that require re-deployment to catch. |
| **DirectLake mode** | Failed in our setup due to OneLake service principal permission issues. Import mode via SQL endpoint is the reliable workaround. This may improve as Microsoft matures the platform. |

### What Still Needs a Human

- **Data source setup** — creating lakehouses, configuring connections, managing credentials
- **Initial project scaffolding** — creating the first PBIP from PBI Desktop or web authoring
- **Visual review and polish** — deploying and checking reports in the browser, requesting fixes
- **Business logic validation** — verifying DAX measures produce correct numbers
- **Credential management** — binding OAuth2 after deployment, managing secrets
- **Governance decisions** — workspace access, RLS rules, refresh schedules

---

## 3. Security & Data Governance Posture

For a US consulting business serving clients, this is the section that matters most.

### Where Data Flows

```
┌─────────────────────────────┐
│  Your Machine (Local)       │
│  ┌───────────────────────┐  │
│  │ Claude Code CLI       │  │
│  │ - Reads/writes TMDL   │  │  No customer data here.
│  │   and PBIR files      │  │  Only schema definitions
│  │ - Sends API calls     │  │  and report structure.
│  └───────────┬───────────┘  │
└──────────────┼──────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
┌─────────────┐   ┌──────────────┐
│ Anthropic   │   │ Microsoft    │
│ (Claude AI) │   │ Fabric/PBI   │
│             │   │ Service      │
│ Sees: TMDL  │   │              │
│ syntax,     │   │ Sees: actual │
│ PBIR JSON,  │   │ customer     │
│ DAX code,   │   │ data in      │
│ schema      │   │ lakehouses   │
│ metadata    │   │ & semantic   │
│             │   │ models       │
│ Does NOT    │   │              │
│ see: actual │   │              │
│ row-level   │   │              │
│ data        │   │              │
└─────────────┘   └──────────────┘
```

### Key Security Properties

**What Claude sees:**
- Table names, column names, data types
- DAX measure definitions
- PBIR visual JSON (page layouts, chart configurations)
- Fabric workspace IDs, item IDs
- API responses (metadata, deployment status)

**What Claude does NOT see:**
- Actual row-level data in lakehouses or semantic models (unless you explicitly run a DAX query via the PowerBIQuery MCP and share results)
- Passwords, connection strings to data sources (these are managed in Fabric Service, not in the TMDL files)
- End-user credentials or PII

**Credential management:**
- Azure service principal credentials (client ID, secret, tenant ID) are stored in a local `.env` file, never committed to Git
- The `.gitignore` excludes `.env` files
- Credentials are used by the fabric-mcp server and deploy scripts to authenticate to Fabric REST APIs
- Service principal has Member role on specific workspaces — scoped access, not tenant-wide admin

**Network exposure:**
- TMDL and PBIR files are sent to Anthropic's API as part of Claude's context (same as any code file in Claude Code)
- Fabric API calls go directly from your machine to Microsoft's endpoints — Claude doesn't proxy them
- No customer data transits through Anthropic unless you explicitly paste it into a conversation

### For Client Engagements

If deploying this approach for a client:

1. **Use the client's own Azure tenant and service principal** — never share credentials across clients
2. **Scope workspace access** — grant the service principal Member role on only the workspaces it needs
3. **Review TMDL before sending to Claude** — if table/column names contain sensitive business terms, the AI will see them (this is true of any AI coding tool)
4. **Don't paste client data into conversations** — use DAX queries in Power BI Service for data validation, not in Claude
5. **Anthropic's data policy** — Claude Code conversations are not used for model training by default. Check [Anthropic's data policy](https://www.anthropic.com/policies) for current terms.
6. **Git repo access** — TMDL and PBIR files are checked into Git. Ensure the repo is private and access-controlled per client engagement.

---

## 4. Scalability: From 1 Report to 50

### What Scales Well

- **TMDL/PBIR as code** — every report is a folder of text files. Git handles branching, merging, and diffing across any number of projects. A team of 5 analysts can work on different reports in parallel branches.
- **Reusable skills** — the PBIR templates and TMDL patterns work for any Power BI project, not just EnS Finance. New projects start from the same skill base.
- **fabric-cicd deployment** — `deploy.py` works with any workspace and any PBIP project. CI/CD pipelines can deploy multiple projects in parallel.
- **MCP servers are stateless** — fabric-mcp starts fresh each session. No accumulated state to manage.

### What Doesn't Scale (Yet)

- **Each report = separate Claude session** — there's no established pattern for an agent managing 50 reports as a portfolio. Each report is a conversation.
- **Context window limits** — MCP server tool definitions consume ~29% of the context window (per Kurt Buhler's analysis). Large models with many tables push the remaining context further.
- **Human review is the bottleneck** — you still deploy and check every report visually. At 50 reports, review burden scales linearly. No automated visual regression testing exists for Power BI.
- **Prompt engineering investment** — each new client domain needs domain-specific context (naming patterns, DAX conventions, visual standards). This is a one-time cost per domain but it's real.
- **Credential rebinding** — the manual OAuth2 step after each semantic model deployment doesn't scale. This is a Microsoft platform limitation.

### Community Perspective

Kurt Buhler (data-goblin, Head of Innovation at Tabular Editor) has been the most candid voice on this:

- Calls agentic Power BI development "nascent technology" with no guaranteed ROI
- Notes agents are better at **refactoring** (bulk renames, adding descriptions, standardizing naming) than **greenfield generation**
- Emphasizes that writing quality prompts can take more time than doing the task manually for simple tasks
- Recommends starting with clear use cases before scaling

SQLBI's whitepaper ("AI Workflows and Agentic Development for Power BI") describes a four-scenario maturity model:
1. Basic chatbot (copy-paste DAX from ChatGPT)
2. Augmented chatbot (MCP servers, custom context)
3. Coding agents (Claude Code autonomously editing TMDL/PBIR) — **this is where we are**
4. Asynchronous agents (triggered via GitHub issues/PRs)

The realistic scaling path: use agents for **mechanical/bulk operations** (renaming, descriptions, translations, template scaffolding) where ROI is clearest, and keep complex DAX authoring and visual design as human-led work with AI assistance.

### Sources
- [SQLBI: Introducing AI and Agentic Development for Power BI](https://www.sqlbi.com/articles/introducing-ai-and-agentic-development-for-business-intelligence/)
- [Tabular Editor: Agentic Development of Semantic Models in Simple Terms](https://tabulareditor.com/blog/agentic-development-of-semantic-models-in-simple-terms)
- [Tabular Editor: AI Agents with Power BI MCP Servers](https://tabulareditor.com/blog/ai-agents-that-work-with-power-bi-semantic-model-mcp-servers)
- [Kasper On BI Podcast: Agentic AI & MCPs with Kurt Buhler](https://www.kasperonbi.com/podcast/agentic-ai-mcps-for-microsoft-fabric-with-kurt-buhler/)

---

## 5. Competitive Positioning

### The Landscape (as of Early 2026)

There are four relevant approaches to AI-assisted Power BI development. They solve different problems and overlap less than you'd expect.

#### Microsoft Copilot in Power BI

**What it does:** Natural language report creation and DAX generation inside the Power BI canvas. You type "show me revenue by region as a bar chart" and it generates the visual in the live report editor.

**Where it wins:** Immediate visual feedback, integrated into the tool users already know, no setup required beyond licensing.

**Where it falls short:** Cannot create or modify semantic models (tables, relationships, hierarchies). Cannot scaffold an entire project. Cannot automate multi-step pipelines. No version control. No cross-platform support.

**Cost:** Requires paid Fabric capacity (F2+, starting ~$262/month). No per-query Copilot charge.

#### Microsoft Fabric Data Agent

**What it does:** A read-only virtual analyst. You point it at up to 5 data sources and it answers natural language questions by generating DAX, SQL, or KQL queries.

**Where it wins:** Business user self-service — non-technical users can ask questions about data without writing queries.

**Where it falls short:** Strictly consumption. Cannot create, modify, or author anything. English only. 25-item limit. Not a development tool at all.

#### Microsoft's Power BI Modeling MCP Server

**What it does:** A local MCP server that connects any AI agent (Claude, Copilot, Gemini) to Power BI Desktop or Fabric via XMLA. Lets agents create/modify tables, columns, measures, relationships. 26 tools including bulk operations.

**Where it wins:** Validated changes via TOM (catches breaking changes before deployment). Bulk operations across hundreds of objects. Works with any MCP-compatible AI agent.

**Where it falls short:** Requires a running Power BI Desktop instance on Windows. No report authoring (PBIR side). Public Preview with potential breaking changes. Context window overhead from 26 tool definitions.

#### Claude Code + PBIR/TMDL (This Approach)

**Where it wins:**
- **Full-stack authoring** — the only approach that creates both the semantic model AND report definition as code, end-to-end
- **Version control native** — everything is text files in Git with meaningful diffs and code review
- **Platform independence** — works on macOS, Linux, Windows; no Power BI Desktop dependency for authoring
- **Pipeline orchestration** — can chain model creation, report building, and deployment in a single workflow
- **No Microsoft AI licensing** — the AI cost is Claude usage, not Fabric capacity; authoring itself is free
- **Composable** — can integrate the Modeling MCP Server, fabric-mcp, DAX query MCP, and community skills freely

**Where it falls short:**
- No live visual preview (write JSON blind, deploy to check)
- PBIR is complex and under-documented; ~85-90% first-try success rate for visuals
- Still needs PBIP scaffold from PBI Desktop or API
- Manual credential rebinding after deployment
- Higher skill floor for the human operator

### Positioning Summary

| | Copilot in PBI | Fabric Data Agent | Modeling MCP | Claude + PBIR/TMDL |
|---|---|---|---|---|
| Creates semantic models | No | No | Yes (needs PBI Desktop) | Yes |
| Creates reports | Yes (limited) | No | No | Yes |
| Full pipeline automation | No | No | No | Yes |
| Git version control | No | No | No | Yes |
| Works without Windows | No | Yes (cloud) | No | Yes |
| Live visual preview | Yes | N/A | N/A | No |
| Setup complexity | Low (built-in) | Low (built-in) | Medium | High |
| Maturity | GA, polished | GA | Public Preview | Early-stage |

**The honest pitch:** This isn't a replacement for Copilot or PBI Desktop. It's a different paradigm — Power BI development as code — that enables automation, version control, and AI-assisted authoring at a level the native tools don't support yet. It's best for teams that want CI/CD, Git workflows, and programmatic control over their BI assets. It's worst for ad-hoc, visual-first exploration.

### Sources
- [Microsoft: Copilot for Power BI overview](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-introduction)
- [Microsoft: Fabric Data Agent concept](https://learn.microsoft.com/en-us/fabric/data-science/concept-data-agent)
- [Microsoft: Power BI MCP servers overview](https://learn.microsoft.com/en-us/power-bi/developer/mcp/mcp-servers-overview)
- [GitHub: powerbi-modeling-mcp](https://github.com/microsoft/powerbi-modeling-mcp)
- [SQLBI: Introducing AI and Agentic Development for Power BI](https://www.sqlbi.com/articles/introducing-ai-and-agentic-development-for-business-intelligence/)
- [Lukas Reese: PBIR Report Builder Claude Skill](https://lukasreese.com/2026/03/14/pbir-report-builder-claude-skill/)
- [Analytical Guy: Fully Automating Power BI Development Using Claude](https://analyticalguy.substack.com/p/fully-automating-power-bi-development)
