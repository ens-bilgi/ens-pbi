"""Deploy PBIP projects to a Fabric/Power BI workspace using fabric-cicd."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(
        description="Deploy PBIP projects to a Fabric/Power BI workspace"
    )
    parser.add_argument(
        "--project",
        type=str,
        required=True,
        help="Path to the PBIP project directory (e.g., projects/sales-dashboard)",
    )
    parser.add_argument(
        "--workspace-id",
        type=str,
        default=os.getenv("POWERBI_WORKSPACE_ID"),
        help="Target workspace ID (defaults to POWERBI_WORKSPACE_ID env var)",
    )
    parser.add_argument(
        "--workspace-name",
        type=str,
        default=None,
        help="Target workspace name (alternative to --workspace-id)",
    )
    parser.add_argument(
        "--environment",
        type=str,
        default="dev",
        help="Environment name for parameterization (default: dev)",
    )
    parser.add_argument(
        "--items",
        type=str,
        nargs="+",
        default=["SemanticModel", "Report"],
        help="Item types to deploy (default: SemanticModel Report)",
    )
    parser.add_argument(
        "--spn-auth",
        action="store_true",
        help="Use service principal auth via Azure CLI (for CI/CD)",
    )
    parser.add_argument(
        "--cleanup-orphans",
        action="store_true",
        help="Remove items from workspace that no longer exist in source",
    )
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    if not project_path.exists():
        print(f"Error: Project path does not exist: {project_path}")
        sys.exit(1)

    if not args.workspace_id and not args.workspace_name:
        print("Error: Provide --workspace-id, --workspace-name, or set POWERBI_WORKSPACE_ID")
        sys.exit(1)

    # Import here so missing deps fail gracefully
    from azure.identity import AzureCliCredential, ClientSecretCredential, InteractiveBrowserCredential
    from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items

    # Choose authentication method
    if args.spn_auth:
        # Service principal via Azure CLI (az login --service-principal)
        credential = AzureCliCredential()
    elif os.getenv("AZURE_CLIENT_SECRET"):
        # Service principal via environment variables
        credential = ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )
    else:
        # Interactive browser login for local development
        credential = InteractiveBrowserCredential()

    workspace_params = {
        "repository_directory": str(project_path),
        "item_type_in_scope": args.items,
        "token_credential": credential,
        "environment": args.environment,
    }

    if args.workspace_id:
        workspace_params["workspace_id"] = args.workspace_id
    else:
        workspace_params["workspace_name"] = args.workspace_name

    print(f"Deploying {args.items} from {project_path}")
    target = "workspace " + (args.workspace_id or args.workspace_name)
    print(f"Target: {target} (environment: {args.environment})")

    workspace = FabricWorkspace(**workspace_params)
    publish_all_items(workspace)

    if args.cleanup_orphans:
        print("Cleaning up orphaned items...")
        unpublish_all_orphan_items(workspace)

    print("Deployment complete.")


if __name__ == "__main__":
    main()
