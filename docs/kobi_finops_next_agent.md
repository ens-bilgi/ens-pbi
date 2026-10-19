# Next-agent prompt — KobiFinOps PBI twin (E1c → E1e)

Copy-paste this into a new Cursor agent (open **`ens-pbi`** as workspace root, or multi-root with the Learning demo).

---

## Prompt

```text
You are continuing the KOBI FinOps Pack 1 Power BI twin (Phase E).

## Context (do not reopen)
- Excel Meeting show-and-tell stays minute-one; this twin is stack proof / upsell.
- Pitch: “Bunu veya benzerini sizin için kuralım.”
- Plan: Learning repo `11_kobi_finops_reporting_demo/docs/pbi_twin_en.md`
- Build host: `/Users/eggs/Developer/ens-bilgi-repo/ens-pbi` (this repo)
- Pack CSV SoT: `…/11_kobi_finops_reporting_demo/packs/food_safety_equipment_reseller/`
- Workspace: E&S Bilgi AI Dev `c44d2ba3-a7ca-4d33-a7ef-8d2080dceefa`
- Auth: ens-pbi/.env SPN (already works)

## Already done
- Lakehouse `KobiFinOps` created; IDs in `docs/kobi_finops_ids.json`
- 17 Pack CSVs uploaded to `Files/kobi_finops/pack1/` and loaded as dbo tables
- Semantic model `KobiFinOps` deployed from `projects/KobiFinOps.SemanticModel` (TMDL)
- Scripts: `scripts/kobi_upload_pack.py`, `scripts/kobi_scaffold_model.py`
- Cursor rules: `.cursor/rules/kobi-finops-twin.mdc` + Learning `.cursor/rules/pbi-twin.mdc`

## Before editing TMDL/PBIR — Read skills
- skills/power-bi-agentic-development/plugins/pbip/skills/tmdl/SKILL.md
- skills/powerbi-skills/pbir-report-builder/SKILL.md
- skills/power-bi-agentic-development/plugins/tabular-editor/skills/bpa-rules/SKILL.md
- skills/skills-for-fabric/skills/powerbi-authoring-cli/SKILL.md
- skills/skills-for-fabric/skills/powerbi-consumption-cli/SKILL.md
Prefer Fabric MCP / TE CLI over hand-edit TMDL when available.

## Your job (in order)
1. Bind / refresh dataset credentials if needed (Import from Lakehouse SQL — same pattern as EnS Finance).
2. Smoke DAX: Ciro, Brut Marj %, Alacak Toplam, Nakit, DSO Proxy — fix Date types on Dim_Takvim if TIMEINTEL fails (CSV dates may be strings).
3. Run BPA mindset (bpa-rules skill) — naming, summarizeBy, hide keys.
4. Create `projects/KobiFinOps.Report` PBIR MVP: pages Yönetim / Nakit / Karışım — TR business labels only (no YTD/DSO/DPO/CCC on visuals).
5. Deploy report; update `docs/kobi_finops_ids.json` + AGENTS.md Current Deployment table.
6. Update Learning repo `docs/pbi_twin_en.md` + roadmap E1c/E1d/E1e status; add one talk-track beat for Excel→PBI flip.
7. Do NOT replace Excel as room default; do NOT leave xlsx with prospects.

## Commands
cd /Users/eggs/Developer/ens-bilgi-repo/ens-pbi
# refresh data from Learning pack:
python scripts/kobi_upload_pack.py
# regenerate+redeploy model:
python scripts/kobi_scaffold_model.py
```

---

## IDs (as of last successful run)

See `docs/kobi_finops_ids.json` in ens-pbi (lakehouse + semantic model). SQL endpoint host matches other lakehouses in the workspace; database name = `KobiFinOps`.
