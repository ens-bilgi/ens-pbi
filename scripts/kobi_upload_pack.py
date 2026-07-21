#!/usr/bin/env python3
"""Upload Pack 1 CSVs to KobiFinOps Lakehouse Files and load as tables.

Requires ens-pbi/.env (AZURE_* + POWERBI_WORKSPACE_ID).
IDs cached in docs/kobi_finops_ids.json after first lakehouse create.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
IDS_PATH = ROOT / "docs" / "kobi_finops_ids.json"
PACK = Path(
    "/Users/eggs/Library/CloudStorage/OneDrive-SharedLibraries-E&SBilgiTeknolojileri/"
    "E&S Bilgi Teknolojileri - General/04_Learning/11_kobi_finops_reporting_demo/"
    "packs/food_safety_equipment_reseller"
)

CSV_TO_TABLE = {
    "fact_sales.csv": "fact_sales",
    "fact_budget.csv": "fact_budget",
    "fact_inventory.csv": "fact_inventory",
    "fact_ar_aging.csv": "fact_ar_aging",
    "fact_ap_aging.csv": "fact_ap_aging",
    "fact_cash.csv": "fact_cash",
    "fact_forecast.csv": "fact_forecast",
    "fact_expenses.csv": "fact_expenses",
    "fact_open_orders.csv": "fact_open_orders",
    "fact_service_base.csv": "fact_service_base",
    "fact_headcount.csv": "fact_headcount",
    "dim_calendar.csv": "dim_calendar",
    "dim_product.csv": "dim_product",
    "dim_customer.csv": "dim_customer",
    "dim_channel.csv": "dim_channel",
    "dim_supplier.csv": "dim_supplier",
    "dim_account.csv": "dim_account",
}


def cred():
    load_dotenv(ROOT / ".env")
    return ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )


def ensure_lakehouse(fabric_token: str, ws: str) -> str:
    h = {"Authorization": f"Bearer {fabric_token}", "Content-Type": "application/json"}
    if IDS_PATH.exists():
        return json.loads(IDS_PATH.read_text())["lakehouse_id"]
    r = requests.get(f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/items", headers=h, timeout=60)
    r.raise_for_status()
    existing = next(
        (i for i in r.json()["value"] if i["displayName"] == "KobiFinOps" and i["type"] == "Lakehouse"),
        None,
    )
    if existing:
        lh = existing["id"]
    else:
        cr = requests.post(
            f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/items",
            headers=h,
            json={"displayName": "KobiFinOps", "type": "Lakehouse", "description": "Pack 1 KOBI FinOps demo CSVs"},
            timeout=60,
        )
        cr.raise_for_status()
        lh = cr.json()["id"]
    IDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    IDS_PATH.write_text(json.dumps({"workspace_id": ws, "lakehouse_id": lh}, indent=2) + "\n")
    return lh


def upload_csvs(storage_token: str, ws: str, lh: str) -> None:
    for p in sorted(PACK.glob("*.csv")):
        rel = f"kobi_finops/pack1/{p.name}"
        url = f"https://onelake.dfs.fabric.microsoft.com/{ws}/{lh}/Files/{rel}"
        h0 = {"Authorization": f"Bearer {storage_token}", "x-ms-version": "2023-11-03", "Content-Length": "0"}
        r = requests.put(url, params={"resource": "file"}, headers=h0, timeout=60)
        if r.status_code not in (200, 201):
            url = f"https://onelake.dfs.fabric.microsoft.com/{ws}/{lh}.Lakehouse/Files/{rel}"
            r = requests.put(url, params={"resource": "file"}, headers=h0, timeout=60)
        r.raise_for_status()
        data = p.read_bytes()
        r2 = requests.patch(
            url,
            params={"action": "append", "position": 0},
            headers={
                "Authorization": f"Bearer {storage_token}",
                "x-ms-version": "2023-11-03",
                "Content-Type": "application/octet-stream",
                "Content-Length": str(len(data)),
            },
            data=data,
            timeout=120,
        )
        r2.raise_for_status()
        r3 = requests.patch(
            url,
            params={"action": "flush", "position": len(data)},
            headers={"Authorization": f"Bearer {storage_token}", "x-ms-version": "2023-11-03", "Content-Length": "0"},
            timeout=60,
        )
        r3.raise_for_status()
        print(f"uploaded {p.name}")


def load_tables(fabric_token: str, ws: str, lh: str) -> None:
    h = {"Authorization": f"Bearer {fabric_token}", "Content-Type": "application/json"}

    def poll(resp: requests.Response) -> None:
        loc = resp.headers.get("Location") or resp.headers.get("Operation-Location")
        if not loc:
            return
        for _ in range(90):
            time.sleep(2)
            pr = requests.get(loc, headers={"Authorization": f"Bearer {fabric_token}"}, timeout=60)
            if pr.status_code != 200:
                continue
            st = pr.json().get("status")
            if st == "Succeeded":
                return
            if st in ("Failed", "Cancelled"):
                raise RuntimeError(pr.text)
        raise TimeoutError(loc)

    for csv_name, table in CSV_TO_TABLE.items():
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{ws}/lakehouses/{lh}/tables/{table}/load"
        body = {
            "relativePath": f"Files/kobi_finops/pack1/{csv_name}",
            "pathType": "File",
            "mode": "Overwrite",
            "formatOptions": {"format": "Csv", "header": True, "delimiter": ","},
        }
        r = requests.post(url, headers=h, json=body, timeout=60)
        if r.status_code == 202:
            poll(r)
        elif r.status_code not in (200, 201):
            raise RuntimeError(f"{table}: {r.status_code} {r.text[:300]}")
        print(f"loaded {table}")


def main() -> None:
    c = cred()
    ws = os.environ["POWERBI_WORKSPACE_ID"]
    fabric = c.get_token("https://api.fabric.microsoft.com/.default").token
    storage = c.get_token("https://storage.azure.com/.default").token
    lh = ensure_lakehouse(fabric, ws)
    print(f"lakehouse={lh}")
    upload_csvs(storage, ws, lh)
    load_tables(fabric, ws, lh)
    print("done")


if __name__ == "__main__":
    main()
