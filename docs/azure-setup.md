# Azure Entra ID Setup for Power BI API Access

This guide walks through registering a service principal that Claude Code (via MCP servers) uses to interact with Power BI Service and Microsoft Fabric.

## Prerequisites

- Azure subscription with Entra ID (Azure AD) access
- Power BI Pro or Premium Per User license
- Power BI tenant admin access (or someone who has it)

## Step 1: Register an Application in Entra ID

1. Go to [Microsoft Entra admin center](https://entra.microsoft.com)
2. Navigate to **Identity > Applications > App registrations**
3. Click **New registration**
4. Fill in:
   - **Name**: `ens-pbi-claude` (or your preferred name)
   - **Supported account types**: "Accounts in this organizational directory only" (single tenant)
   - **Redirect URI**: Select "Web" and enter `http://localhost` (needed for device code flow)
5. Click **Register**
6. Note down:
   - **Application (client) ID** → this becomes `AZURE_CLIENT_ID`
   - **Directory (tenant) ID** → this becomes `AZURE_TENANT_ID`

## Step 2: Create a Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **New client secret**
3. Add a description (e.g., "ens-pbi-claude") and set expiration
4. Click **Add**
5. **Copy the Value immediately** — it won't be shown again
   - This becomes `AZURE_CLIENT_SECRET`

## Step 3: Add API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission** > **Power BI Service**
3. Add these **Delegated permissions**:
   - `Dataset.ReadWrite.All`
   - `Workspace.ReadWrite.All`
   - `Report.ReadWrite.All`
   - `Content.Create`
   - `Dataflow.ReadWrite.All`
4. Add these **Application permissions**:
   - `Tenant.ReadWrite.All`
5. Click **Grant admin consent for [your org]** (requires admin role)

## Step 4: Create a Security Group

1. Go to **Identity > Groups > All groups**
2. Click **New group**
   - **Group type**: Security
   - **Group name**: `ens-pbi-service-principals`
   - **Members**: Add the app registration you created in Step 1
3. Click **Create**

## Step 5: Enable Service Principals in Power BI Admin Portal

1. Go to [Power BI Admin Portal](https://app.powerbi.com/admin-portal)
2. Navigate to **Tenant settings**
3. Under **Developer settings**:
   - Enable **"Allow service principals to use Power BI APIs"**
   - Apply to the security group from Step 4
4. Under **Integration settings**:
   - Enable **"Dataset Execute Queries REST API"**
   - Apply to the security group from Step 4
5. Under **Admin API settings** (if you need admin-level operations):
   - Enable **"Allow service principals to use read-only admin APIs"**
   - Apply to the security group

## Step 6: Grant Workspace Access

For each Power BI workspace you want Claude to access:

1. Open the workspace in [Power BI Service](https://app.powerbi.com)
2. Click **Access** (or Manage access)
3. Add your app registration by searching for its name (`ens-pbi-claude`)
4. Assign **Member** or **Admin** role
   - **Member**: Can create/edit/delete content
   - **Admin**: Full control including managing access

## Step 7: Configure Your Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Fill in your credentials:
   ```
   AZURE_TENANT_ID=<from Step 1>
   AZURE_CLIENT_ID=<from Step 1>
   AZURE_CLIENT_SECRET=<from Step 2>
   POWERBI_WORKSPACE_ID=<your target workspace ID>
   ```

   To find a workspace ID: open the workspace in Power BI Service — the URL contains it:
   `https://app.powerbi.com/groups/<workspace-id>/...`

## Step 8: Set Up Fabric Git Integration (Optional)

If you want commits to this repo to auto-deploy to Power BI:

1. Open your workspace in Power BI Service
2. Click **Workspace settings** > **Git integration**
3. Connect to your GitHub or Azure DevOps repo
4. Select the branch and folder to sync
5. Power BI will sync PBIP content from the repo to the workspace

See [Fabric Git integration docs](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/intro-to-git-integration) for details.

## Troubleshooting

### 401 Unauthorized
- Check that admin consent was granted (Step 3)
- Verify the service principal is in the security group (Step 4)
- Confirm tenant settings are enabled (Step 5)

### 403 Forbidden
- Check workspace access (Step 6) — the service principal needs Member or Admin role
- Some operations require Power BI Premium/PPU capacity

### Token acquisition fails
- Verify `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` are correct
- Check that the client secret hasn't expired
