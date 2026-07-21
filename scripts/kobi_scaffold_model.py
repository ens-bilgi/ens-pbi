#!/usr/bin/env python3
"""Scaffold + deploy KobiFinOps semantic model (TMDL) over Lakehouse SQL endpoint.

Creates projects/KobiFinOps.SemanticModel from Pack CSV schemas + DAX_Measures pack.
Deploys via Fabric create / updateDefinition (same pattern as deploy_api.py).
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from pathlib import Path

import requests
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PROJ = ROOT / "projects" / "KobiFinOps.SemanticModel"
IDS_PATH = ROOT / "docs" / "kobi_finops_ids.json"
PACK = Path(
    "/Users/eggs/Library/CloudStorage/OneDrive-SharedLibraries-E&SBilgiTeknolojileri/"
    "E&S Bilgi Teknolojileri - General/04_Learning/11_kobi_finops_reporting_demo/"
    "packs/food_safety_equipment_reseller"
)

# Lakehouse table → model table display name (matches Excel DAX_Measures naming)
TABLES = [
    ("fact_sales", "Fact_Satis"),
    ("fact_budget", "Fact_Butce"),
    ("fact_inventory", "Fact_Stok"),
    ("fact_ar_aging", "Fact_Alacak"),
    ("fact_ap_aging", "Fact_Borc"),
    ("fact_cash", "Fact_Nakit"),
    ("fact_forecast", "Fact_Tahmin"),
    ("dim_calendar", "Dim_Takvim"),
    ("dim_product", "Dim_Urun"),
    ("dim_customer", "Dim_Musteri"),
    ("dim_channel", "Dim_Kanal"),
    ("dim_supplier", "Dim_Tedarikci"),
    ("dim_account", "Dim_Hesap"),
]

# rough type map by column name suffix / known fields
STRINGISH = {
    "SaleId", "OrderId", "AccountKey", "AccountName", "AccountType", "ProductKey", "ProductName",
    "Family", "SubFamily", "ABC", "CustomerKey", "CustomerName", "Segment", "City", "ChannelKey",
    "ChannelName", "ChannelGroup", "SupplierKey", "SupplierName", "Country", "Category", "Currency",
    "Scenario", "Source", "Status", "MonthNameTR", "YearMonth",
}
DATEISH = {"Date", "AsOfDate"}
INTISH = {"Year", "Month", "Sort", "SortKey", "Qty", "OnHandQty", "LeadTimeDays", "InstallYear",
          "CalibrationDueInDays", "PaymentTermsDays", "IsActual", "IsForecast", "IsYTD",
          "IsStrategic", "IsAttachEligible", "HasActiveContract", "Headcount", "SalesTeam",
          "ServiceTeam", "WarehouseAdmin", "Other"}

MEASURES = [
    ("Ciro", "SUM ( Fact_Satis[RevenueTRY] )", "#,##0"),
    ("COGS", "SUM ( Fact_Satis[COGSTRY] )", "#,##0"),
    ("Brut Kar", "[Ciro] - [COGS]", "#,##0"),
    ("Brut Marj %", "DIVIDE ( [Brut Kar], [Ciro] )", "0.0%"),
    ("Ciro YTD", "TOTALYTD ( [Ciro], Dim_Takvim[Date] )", "#,##0"),
    ("Ciro Onceki Ay", "CALCULATE ( [Ciro], DATEADD ( Dim_Takvim[Date], -1, MONTH ) )", "#,##0"),
    ("Ciro MoM %", "DIVIDE ( [Ciro] - [Ciro Onceki Ay], [Ciro Onceki Ay] )", "0.0%"),
    ("Ciro Butce", 'CALCULATE ( SUM ( Fact_Butce[AmountTRY] ), Fact_Butce[AccountKey] = "REV" )', "#,##0"),
    ("VTB Ciro", "[Ciro] - [Ciro Butce]", "#,##0"),
    ("VTB Ciro %", "DIVIDE ( [VTB Ciro], [Ciro Butce] )", "0.0%"),
    ("Stok Tutari", "SUM ( Fact_Stok[InventoryValueTRY] )", "#,##0"),
    ("Alacak Toplam", "SUM ( Fact_Alacak[TotalARTRY] )", "#,##0"),
    ("DSO Proxy", "DIVIDE ( [Alacak Toplam], DIVIDE ( [Ciro], 30 ) )", "0.0"),
    ("Borc Toplam", "SUM ( Fact_Borc[TotalAPTRY] )", "#,##0"),
    ("DPO Proxy", "DIVIDE ( [Borc Toplam], DIVIDE ( [COGS], 30 ) )", "0.0"),
    ("DIO Proxy", "DIVIDE ( [Stok Tutari], DIVIDE ( [COGS], 30 ) )", "0.0"),
    ("CCC", "[DSO Proxy] + [DIO Proxy] - [DPO Proxy]", "0.0"),
    ("NWC", "[Alacak Toplam] + [Stok Tutari] - [Borc Toplam]", "#,##0"),
    ("Nakit", "SUM ( Fact_Nakit[CashTRY] )", "#,##0"),
    ("Ciro Ekipman", 'CALCULATE ( [Ciro], Dim_Urun[Family] = "Ekipman" )', "#,##0"),
    ("Ciro Sarf", 'CALCULATE ( [Ciro], Dim_Urun[Family] = "Sarf" )', "#,##0"),
    ("Ciro Hizmet", 'CALCULATE ( [Ciro], Dim_Urun[Family] = "Hizmet" )', "#,##0"),
]

RELATIONSHIPS = [
    ("Fact_Satis", "Date", "Dim_Takvim", "Date"),
    ("Fact_Satis", "ProductKey", "Dim_Urun", "ProductKey"),
    ("Fact_Satis", "CustomerKey", "Dim_Musteri", "CustomerKey"),
    ("Fact_Satis", "ChannelKey", "Dim_Kanal", "ChannelKey"),
    ("Fact_Butce", "Date", "Dim_Takvim", "Date"),
    ("Fact_Butce", "AccountKey", "Dim_Hesap", "AccountKey"),
    ("Fact_Stok", "Date", "Dim_Takvim", "Date"),
    ("Fact_Stok", "ProductKey", "Dim_Urun", "ProductKey"),
    ("Fact_Alacak", "Date", "Dim_Takvim", "Date"),
    ("Fact_Alacak", "CustomerKey", "Dim_Musteri", "CustomerKey"),
    ("Fact_Borc", "Date", "Dim_Takvim", "Date"),
    ("Fact_Borc", "SupplierKey", "Dim_Tedarikci", "SupplierKey"),
    ("Fact_Nakit", "Date", "Dim_Takvim", "Date"),
    ("Fact_Tahmin", "Date", "Dim_Takvim", "Date"),
]


def tag() -> str:
    return str(uuid.uuid4())


def dtype(col: str) -> str:
    if col in DATEISH:
        return "dateTime"
    if col in INTISH or col.endswith("Days") or col.startswith("Is") or col.startswith("Has"):
        return "int64"
    if col in STRINGISH or col.endswith("Key") or col.endswith("Name") or col.endswith("Id"):
        return "string"
    if col.endswith("TRY") or col.endswith("Rate") or col.endswith("Pct") or col in {"TargetMargin", "KDVRate"}:
        return "double"
    return "string"


def summarize(col: str, dt: str) -> str:
    if dt in ("double", "int64") and col.endswith("TRY"):
        return "sum"
    if col in {"Qty", "OnHandQty", "Headcount"}:
        return "sum"
    return "none"


def read_header(csv_name: str) -> list[str]:
    text = (PACK / csv_name).read_text(encoding="utf-8-sig").splitlines()[0]
    return [c.strip() for c in text.split(",")]


def write_table_tmdl(lake_table: str, model_name: str, cols: list[str], with_measures: bool = False) -> str:
    lines = [f"table {model_name}"]
    if model_name == "Dim_Takvim":
        lines.append("\tdataCategory: Time")
    lines += [f"\tlineageTag: {tag()}", ""]
    for col in cols:
        dt = dtype(col)
        sb = summarize(col, dt)
        q = f"'{col}'" if any(ch in col for ch in " -") else col
        lines += [
            f"\tcolumn {q}",
            f"\t\tdataType: {dt}",
        ]
        if col == "Date" and model_name == "Dim_Takvim":
            lines.append("\t\tisKey")
        lines += [
            f"\t\tlineageTag: {tag()}",
            f"\t\tsummarizeBy: {sb}",
            f"\t\tsourceColumn: {col}",
            "",
            "\t\tannotation SummarizationSetBy = Automatic",
            "",
        ]
        if col == "Date" and model_name == "Dim_Takvim":
            # insert annotation before blank - already added Automatic; add date hint
            lines.insert(-1, "\t\tannotation UnderlyingDateTimeDataType = Date")
            lines.append("")

    if with_measures:
        for name, expr, fmt in MEASURES:
            qn = f"'{name}'" if " " in name or "%" in name else name
            # indent DAX expression lines for TMDL
            expr_lines = expr.strip().split("\n")
            lines.append(f"\t/// {name}")
            lines.append(f"\tmeasure {qn} =")
            if len(expr_lines) == 1:
                lines.append(f"\t\t\t{expr_lines[0]}")
            else:
                for el in expr_lines:
                    lines.append(f"\t\t\t{el}")
            lines += [
                f"\t\tformatString: {fmt}",
                f"\t\tdisplayFolder: KPI",
                f"\t\tlineageTag: {tag()}",
                "",
            ]

    lines += [
        f"\tpartition {model_name} = m",
        "\t\tmode: import",
        "\t\tqueryGroup: Tables",
        "\t\tsource =",
        "\t\t\t\tlet",
        "\t\t\t\t    Source = Sql.Database(SqlEndpoint, Database),",
        f'\t\t\t\t    Data = Source{{[Schema="dbo",Item="{lake_table}"]}}[Data]',
        "\t\t\t\tin",
        "\t\t\t\t    Data",
        "",
    ]
    return "\n".join(lines) + "\n"


def scaffold(sql_endpoint: str, database: str) -> None:
    if PROJ.exists():
        # wipe definition for clean regenerate
        import shutil

        shutil.rmtree(PROJ)
    (PROJ / "definition" / "tables").mkdir(parents=True)
    (PROJ / "definition" / "roles").mkdir(parents=True)

    (PROJ / "definition.pbism").write_text(
        json.dumps({"version": "4.2", "settings": {"qnaEnabled": True}}, indent=4) + "\n",
        encoding="utf-8",
    )
    (PROJ / "definition" / "database.tmdl").write_text(
        "database\n\tcompatibilityLevel: 1600\n",
        encoding="utf-8",
    )

    refs = "\n".join(f"ref table {name}" for _, name in TABLES)
    model = f"""model Model
\tculture: tr-TR
\tdefaultPowerBIDataSourceVersion: powerBI_V3
\tdiscourageImplicitMeasures
\tsourceQueryCulture: en-US

{refs}

queryGroup Tables

\tannotation PBI_QueryGroupOrder = 0

queryGroup Parameters

\tannotation PBI_QueryGroupOrder = 1

expression SqlEndpoint = "{sql_endpoint}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tlineageTag: {tag()}
\tqueryGroup: Parameters

\tannotation PBI_NavigationStepName = Navigation
\tannotation PBI_ResultType = Text

expression Database = "{database}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
\tlineageTag: {tag()}
\tqueryGroup: Parameters

\tannotation PBI_NavigationStepName = Navigation
\tannotation PBI_ResultType = Text
"""
    (PROJ / "definition" / "model.tmdl").write_text(model, encoding="utf-8")

    csv_for = {lake: f"{lake}.csv" for lake, _ in TABLES}
    for lake, model_name in TABLES:
        cols = read_header(csv_for[lake])
        text = write_table_tmdl(lake, model_name, cols, with_measures=(model_name == "Fact_Satis"))
        (PROJ / "definition" / "tables" / f"{model_name}.tmdl").write_text(text, encoding="utf-8")

    blocks = []
    for i, (fr, fc, to, tc) in enumerate(RELATIONSHIPS, start=1):
        rid = f"r{i:08d}-0000-0000-0000-000000000001"
        blocks.append(
            "\n".join(
                [
                    f"relationship {rid}",
                    f"\tfromColumn: {fr}.{fc}",
                    f"\ttoColumn: {to}.{tc}",
                    "",
                ]
            )
        )
    (PROJ / "definition" / "relationships.tmdl").write_text("\n".join(blocks), encoding="utf-8")
    print(f"scaffolded {PROJ}")


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def collect_parts(base: Path) -> list[dict]:
    parts = []
    def_path = base / "definition.pbism"
    parts.append({"path": "definition.pbism", "payload": b64(def_path.read_text(encoding="utf-8")), "payloadType": "InlineBase64"})
    for f in sorted((base / "definition").rglob("*")):
        if f.is_file():
            rel = str(f.relative_to(base))
            parts.append({"path": rel, "payload": b64(f.read_text(encoding="utf-8")), "payloadType": "InlineBase64"})
    return parts


def poll(url: str, token: str) -> bool:
    h = {"Authorization": f"Bearer {token}"}
    for _ in range(60):
        time.sleep(3)
        r = requests.get(url, headers=h, timeout=60)
        if r.status_code != 200:
            continue
        st = r.json().get("status")
        if st == "Succeeded":
            return True
        if st in ("Failed", "Cancelled"):
            print(r.text)
            return False
    return False


def deploy(token: str, ws: str) -> str:
    h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    ids = json.loads(IDS_PATH.read_text()) if IDS_PATH.exists() else {}
    model_id = ids.get("semantic_model_id")

    # find existing
    r = requests.get(f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/items", headers=h, timeout=60)
    r.raise_for_status()
    existing = next(
        (i for i in r.json()["value"] if i["displayName"] == "KobiFinOps" and i["type"] == "SemanticModel"),
        None,
    )
    parts = collect_parts(PROJ)

    if existing:
        model_id = existing["id"]
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/semanticModels/{model_id}/updateDefinition"
        resp = requests.post(url, headers=h, json={"definition": {"parts": parts}}, timeout=120)
        print("updateDefinition", resp.status_code)
        if resp.status_code == 202:
            loc = resp.headers.get("Location") or resp.headers.get("Operation-Location")
            ok = poll(loc, token)
            print("update", "ok" if ok else "fail")
        elif resp.status_code not in (200, 201):
            print(resp.text[:500])
            raise SystemExit(1)
    else:
        body = {
            "displayName": "KobiFinOps",
            "description": "Pack 1 KOBI FinOps semantic model twin",
            "definition": {"parts": parts},
        }
        resp = requests.post(
            f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/semanticModels",
            headers=h,
            json=body,
            timeout=120,
        )
        print("create semanticModel", resp.status_code, resp.text[:300])
        if resp.status_code == 202:
            loc = resp.headers.get("Location") or resp.headers.get("Operation-Location")
            if not poll(loc, token):
                raise SystemExit("create failed")
            # re-list
            r2 = requests.get(f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/items", headers=h, timeout=60)
            existing = next(
                (i for i in r2.json()["value"] if i["displayName"] == "KobiFinOps" and i["type"] == "SemanticModel"),
                None,
            )
            model_id = existing["id"]
        elif resp.status_code in (200, 201):
            model_id = resp.json()["id"]
        else:
            raise SystemExit(1)

    ids["workspace_id"] = ws
    ids["semantic_model_id"] = model_id
    IDS_PATH.write_text(json.dumps(ids, indent=2) + "\n")
    print("semantic_model_id", model_id)
    return model_id


def main() -> None:
    load_dotenv(ROOT / ".env")
    c = ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )
    ws = os.environ["POWERBI_WORKSPACE_ID"]
    fabric = c.get_token("https://api.fabric.microsoft.com/.default").token
    ids = json.loads(IDS_PATH.read_text())
    lh = ids["lakehouse_id"]
    # SQL endpoint + database name = lakehouse display name
    r = requests.get(
        f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/lakehouses/{lh}",
        headers={"Authorization": f"Bearer {fabric}"},
        timeout=60,
    )
    r.raise_for_status()
    props = r.json()["properties"]["sqlEndpointProperties"]
    sql = props["connectionString"]
    database = "KobiFinOps"
    print("sql", sql, "db", database)
    scaffold(sql, database)
    deploy(fabric, ws)


if __name__ == "__main__":
    main()
