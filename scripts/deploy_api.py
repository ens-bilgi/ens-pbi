"""Deploy semantic model and report via Fabric REST API (updateDefinition)."""

import base64
import json
import os
import sys
import time
from pathlib import Path

import requests
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv

load_dotenv(Path("/Users/eggs/Desktop/ens-pbi/.env"))


def get_token():
    cred = ClientSecretCredential(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )
    return cred.get_token("https://analysis.windows.net/powerbi/api/.default").token


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def collect_parts(base_dir: Path, definition_file: str) -> list[dict]:
    """Collect all files under an item directory as API parts."""
    parts = []
    # Add the top-level definition file (definition.pbism or definition.pbir)
    def_path = base_dir / definition_file
    if def_path.exists():
        parts.append({
            "path": definition_file,
            "payload": b64(def_path.read_text(encoding="utf-8")),
            "payloadType": "InlineBase64",
        })

    # Add all files under definition/
    def_dir = base_dir / "definition"
    if def_dir.exists():
        for f in sorted(def_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(base_dir)
                parts.append({
                    "path": str(rel),
                    "payload": b64(f.read_text(encoding="utf-8")),
                    "payloadType": "InlineBase64",
                })
    return parts


def poll_operation(url: str, headers: dict, timeout: int = 120):
    """Poll a long-running operation until completion."""
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            body = r.json()
            status = body.get("status", "Unknown")
            if status == "Succeeded":
                print(f"  -> Succeeded")
                return True
            elif status in ("Failed", "Cancelled"):
                print(f"  -> {status}: {body}")
                return False
            else:
                print(f"  -> {status}...")
        time.sleep(3)
    print("  -> Timed out")
    return False


def update_definition(ws_id: str, item_type: str, item_id: str, parts: list[dict], token: str):
    """Call updateDefinition API for a semantic model or report."""
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{ws_id}/{item_type}s/{item_id}/updateDefinition"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {"definition": {"parts": parts}}

    print(f"Updating {item_type} {item_id} ({len(parts)} parts)...")
    r = requests.post(url, headers=headers, json=body)

    if r.status_code == 200:
        print("  -> Updated immediately")
        return True
    elif r.status_code == 202:
        location = r.headers.get("Location")
        if location:
            print(f"  -> Accepted, polling...")
            return poll_operation(location, headers)
        print("  -> Accepted (no Location header)")
        return True
    else:
        print(f"  -> Error {r.status_code}: {r.text}")
        return False


def main():
    projects_dir = Path(__file__).resolve().parent.parent / "projects"
    ws_id = os.environ["POWERBI_WORKSPACE_ID"]
    sm_id = "befbcd38-708e-40e6-9826-f61f62a4b726"
    rpt_id = "3b0876f2-9bfd-4769-ab94-7ff8f2bbd2b4"

    token = get_token()

    # Deploy semantic model
    sm_dir = projects_dir / "EnSFinance.SemanticModel"
    sm_parts = collect_parts(sm_dir, "definition.pbism")
    ok1 = update_definition(ws_id, "semanticModel", sm_id, sm_parts, token)

    # Deploy report
    rpt_dir = projects_dir / "EnSFinance.Report"
    rpt_parts = collect_parts(rpt_dir, "definition.pbir")
    ok2 = update_definition(ws_id, "report", rpt_id, rpt_parts, token)

    if ok1 and ok2:
        print("\nBoth deployed successfully. Refresh the report in the browser.")
    else:
        print("\nSome deployments failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
