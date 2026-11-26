# Edgebook

IF THE UI LOOKS WEIRD! REMEMBER TO HARD RELOAD!! cmd + shift + R

A paper-trading desk for prediction markets. Edgebook pulls markets, asks Jev (TypeSafe AI) for its own probability on each one, places paper bets where Jev disagrees with the crowd, and scores whether Jev was actually better than the market once markets resolve.

**Pipeline:** fetch markets -> gather news -> ask Jev -> decide bets -> settle bets -> score Jev

## Quick start

From a clean clone, start Docker Desktop. On Apple Silicon, enable Rosetta for the SQL Server image.

```bash
cp .env.example .env
docker compose up --build
```

Use three distinct local passwords in the copied file before the first boot. Intel listens on port 8001 and Book on 8002. Check `/health` on each. Port 8080 serves a placeholder for the static UI. The default sources use fixtures and the stub forecaster.

SQL Server keeps both databases in the named volume `sql-data`. Use `docker compose down` to stop the stack and keep the rows.

## Azure setup for Assignment 2

On November 26, Azure CLI listed the enabled Azure for Students subscription, the resource group, the SQL server and the two application databases in France Central. Both databases had a one-vCore serverless SKU, the free limit enabled, and AutoPause on exhaustion. TCP port 1433 was reachable from the development machine. ADR 7 records the earlier encrypted driver check.

The subscription policy allows France Central. All five providers below were registered. The regional Container Apps quota reported one managed environment allowed and zero used. GitHub listed zero repository Actions variables and zero repository Actions secrets. These are the read-only inventory commands used for those checks:

```bash
az account show --query '{subscription:name,state:state}'
az resource list -g rg-jcruz-ieu2024 --query '[].{name:name,type:type,location:location}'
az policy assignment list --query "[?contains(displayName,'region')].parameters"
az sql db list -g rg-jcruz-ieu2024 -s jcruz-ieu2024-sql \
    --query '[].{name:name,sku:sku.name,free:useFreeLimit,onExhaustion:freeLimitExhaustionBehavior}'
az rest --method get --url "https://management.azure.com/subscriptions/$(az account show --query id -o tsv)/providers/Microsoft.App/locations/francecentral/usages?api-version=2024-03-01"
gh secret list --json name
gh variable list --json name
```

### Initial setup for Javi to run

Use Bash or Azure Cloud Shell. These are the remaining setup commands. Use the existing SQL server and databases. Run from the repository root for the GitHub steps. Keep the same Bash session for the variables below.

```bash
set -euo pipefail
prefix=jcruz-ieu2024
group=rg-$prefix
region=francecentral
storage=jcruzieu2024ui
repo=javocruz/DevopsAssignment
scope=$(az group show -n "$group" --query id -o tsv)

for provider in Microsoft.App Microsoft.OperationalInsights Microsoft.Sql Microsoft.Storage Microsoft.ManagedIdentity; do
    az provider register -n "$provider" --wait
done
az extension add -n containerapp --upgrade
az storage account create -g "$group" -n "$storage" -l "$region" --sku Standard_LRS --kind StorageV2 -o none
az storage blob service-properties update --account-name "$storage" --static-website --index-document index.html -o none
az storage account show -g "$group" -n "$storage" --query primaryEndpoints.web -o tsv
az containerapp env create -g "$group" -n "$prefix-env" -l "$region" --logs-destination none -o none
for svc in intel book; do
    az containerapp create -g "$group" -n "$prefix-$svc" --environment "$prefix-env" \
        --image mcr.microsoft.com/k8se/quickstart:latest --ingress external --target-port 8000 \
        --min-replicas 0 --max-replicas 1 --cpu 0.25 --memory 0.5Gi -o none
done
```

Port 8000 is the Edgebook image port. Check the deployed service's health after the pipeline replaces the placeholder. The application supplies the browser CORS policy.

### SQL users and encrypted login check

From an allowed client IP, connect directly to each application database as its SQL administrator. Use the existing contained users if already provisioned. In the Bash session, the following creates missing users, grants the three database roles and checks each service password before storing it in GitHub. Use an ODBC-based `sqlcmd` with encryption enabled, such as the one under `/opt/mssql-tools18/bin` in the SQL Server container. The administrative password is entered locally at a hidden prompt.

```bash
host="$prefix-sql.database.windows.net"
admin=$(az sql server show -g "$group" -n "$prefix-sql" --query administratorLogin -o tsv)
read -rsp 'SQL administrator password: ' SQLCMDPASSWORD; echo
export SQLCMDPASSWORD
for svc in intel book; do
    database="$prefix-$svc-db"
    read -rsp "$svc service password (existing, or new for first setup): " pw; echo
    hex=$(printf '%s' "$pw" | iconv -f UTF-8 -t UTF-16LE | od -An -v -tx1 | tr -d ' \n')
    sqlcmd -S "$host" -d "$database" -U "$admin" -N -b <<SQL
IF USER_ID(N'$svc') IS NULL
BEGIN
    DECLARE @p NVARCHAR(MAX) = CONVERT(NVARCHAR(MAX), 0x$hex);
    IF DATALENGTH(@p) > 256 THROW 50000, 'Password too long', 1;
    DECLARE @cmd NVARCHAR(MAX) = N'CREATE USER [$svc] WITH PASSWORD = ' + QUOTENAME(@p, '''');
    EXEC (@cmd);
END;
ALTER ROLE db_ddladmin ADD MEMBER [$svc];
ALTER ROLE db_datareader ADD MEMBER [$svc];
ALTER ROLE db_datawriter ADD MEMBER [$svc];
SQL
    SQLCMDPASSWORD="$pw" sqlcmd -S "$host" -d "$database" -U "$svc" -N -b \
        -Q "SELECT DB_NAME() AS database_name, USER_NAME() AS service_user"
    secret_name=$(printf '%s_DB_PASSWORD' "$svc" | tr '[:lower:]' '[:upper:]')
    printf '%s' "$pw" | gh secret set "$secret_name" --repo "$repo"
done
unset SQLCMDPASSWORD pw hex
# Run after the last direct local SQL check:
az sql server firewall-rule delete -g "$group" -s "$prefix-sql" -n AllowHome
```

### GitHub identity and permissions

```bash
az identity create -g "$group" -n "$prefix-github" -l "$region" -o none
principal=$(az identity show -g "$group" -n "$prefix-github" --query principalId -o tsv)
client=$(az identity show -g "$group" -n "$prefix-github" --query clientId -o tsv)
az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal \
    --role Contributor --scope "$scope" -o none
storage_id=$(az storage account show -g "$group" -n "$storage" --query id -o tsv)
az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal \
    --role 'Storage Blob Data Contributor' --scope "$storage_id" -o none

owner_id=$(gh api "repos/$repo" --jq .owner.id)
repo_id=$(gh api "repos/$repo" --jq .id)
for form in names ids; do
    subject="repo:${repo}:ref:refs/heads/main"
    if [[ $form == ids ]]; then
        subject="repo:${repo%/*}@$owner_id/${repo#*/}@$repo_id:ref:refs/heads/main"
    fi
    az identity federated-credential create -g "$group" --identity-name "$prefix-github" \
        -n "github-main-$form" --issuer https://token.actions.githubusercontent.com \
        --subject "$subject" --audiences api://AzureADTokenExchange -o none
done
printf '%s' "$client" | gh secret set AZURE_CLIENT_ID --repo "$repo"
az account show --query tenantId -o tsv | gh secret set AZURE_TENANT_ID --repo "$repo"
az account show --query id -o tsv | gh secret set AZURE_SUBSCRIPTION_ID --repo "$repo"
gh secret set ADMIN_TOKEN --repo "$repo"
gh variable set PREFIX --body "$prefix" --repo "$repo"
gh variable set RESOURCE_GROUP --body "$group" --repo "$repo"
gh variable set UI_STORAGE --body "$storage" --repo "$repo"
for professor in amartini@faculty.ie.edu bserra@faculty.ie.edu; do
    az role assignment create --assignee "$professor" --role Reader --scope "$scope" -o none
done
```

### Pipeline handoff

The reusable workflow `.github/workflows/azure-release.yml` implements publication and deployment. The C14 caller must grant `contents: read`, `packages: write` and `id-token: write`, call it with `needs: ci` and `secrets: inherit`. The CD job on `main` needs a passing CI run on the same SHA, GitHub OIDC login, and public GHCR images named `ghcr.io/javocruz/jcruz-ieu2024-{intel,book}:<sha>` built for Linux amd64 with `provenance: false`. After login and publication, run `bash scripts/deploy-azure.sh` with the three repository variables and the two database passwords and admin token in the job environment. The script sets the apps' images and secret references, checks both health responses for the deployed SHA, and publishes the UI. The static dashboard reads `window.EDGEBOOK_CONFIG.intelUrl` and `bookUrl` once implemented. Save the actual failed and successful run links. Before migration 002, save the original settled bet rows from the deployment running only 001.

## Assignment 1 reference

The following settings and routes describe the original single-process version.

## Keys

Set keys in the shell. The app does not read a `.env` file. Do not commit them.

```bash
export TYPESAFE_API_KEY=your-key    # only for DECIDER=jev
export THENEWSAPI_TOKEN=your-token  # only for NEWS_SOURCE=thenewsapi
export ADMIN_TOKEN=your-token       # optional lock on POST routes
```

A missing `TYPESAFE_API_KEY` falls back to the stub. A missing `THENEWSAPI_TOKEN` falls back to fixture news. An empty `ADMIN_TOKEN` leaves POST routes open.

## Data

`DATA_DIR` is the only folder the app writes. The database file is `edgebook.db` inside it. Default is `./data`.

```bash
DATA_DIR=/tmp/edgebook python app.py
```

In Assignment 2, mount a volume at `DATA_DIR` so a container restart does not wipe the database.

## Configuration

Every variable is read in `config.py`. Invalid values raise `ValueError` and name the variable.

| Var | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | port uvicorn binds on `0.0.0.0` |
| `DATA_DIR` | `./data` | folder for `edgebook.db` |
| `LOG_LEVEL` | `INFO` | stdout logging level |
| `ADMIN_TOKEN` | empty | if set, every POST route needs header `X-Admin-Token` |
| `MARKET_SOURCE` | `fixture` | `fixture` or `polymarket` |
| `POLYMARKET_LIMIT` | `50` | markets pulled in polymarket mode |
| `NEWS_SOURCE` | `fixture` | `none`, `fixture`, or `thenewsapi` |
| `THENEWSAPI_TOKEN` | empty | needed only for `NEWS_SOURCE=thenewsapi` |
| `NEWS_ARTICLES` | `3` | headlines per market |
| `NEWS_MAX_CALLS_PER_RUN` | `20` | hard cap on TheNewsAPI calls per request |
| `DECIDER` | `stub` | `stub` or `jev` |
| `TYPESAFE_API_KEY` | empty | needed only for `DECIDER=jev` |
| `TYPESAFE_BASE_URL` | `https://api.typesafe.ai/v1/systemone` | Jev endpoint |
| `JEV_MODEL` | `jev-latest` | model name sent in the request |
| `HTTP_TIMEOUT` | `10` | seconds, every external call |
| `ESTIMATE_BATCH_LIMIT` | `20` | max markets per `/estimates/run` call |
| `EDGE_THRESHOLD` | `0.08` | minimum absolute edge to bet |
| `MIN_CONFIDENCE` | `0.6` | minimum Jev confidence to bet |
| `MIN_INFO` | `0.4` | minimum info_score (0 to 1) to bet |
| `BASE_STAKE` | `10` | stake at exactly the threshold edge |
| `MAX_STAKE` | `50` | cap on any single bet |

## Tests and coverage

```bash
pytest --cov=. --cov-report=term-missing
```

Total coverage: 97% (62 tests).

## Structure

- `app.py`: start the server, `/healthz`, static files
- `config.py`: env vars
- `db.py`: SQLite, schema version
- `security.py`: optional `ADMIN_TOKEN` on POST routes
- `contracts.py`: `Estimate` and `Resolution`, the only handoff
- `pipeline.py`: the only file that imports both `intel/` and `book/`, plus `GET /`
- `intel/`: markets, news, estimates
- `book/`: edge, settlement, scoring, bets
- `templates/` and `static/`: the dashboard. It only calls JSON routes. Charts are Chart.js 4.5.1, saved in `static/vendor/chart.min.js` and loaded from that file.
- `fixtures/resolved_markets.json`: offline markets
- `tests/`: offline tests, with saved API samples in `tests/data/`

Diagrams: [architecture](docs/diagrams/architecture.md) and [database schema](docs/diagrams/db-schema.md).

## Project docs

Graded docs stay at the project root. The spec is numbered, so read it in order.

- `README.md`: how to run the app
- `ADR.md`: the architecture decisions, written on the day each one is made
- `AI_USAGE.md`: one entry per AI interaction. The last field of each entry is written by hand
- `AGENTS.md`: instructions for coding agents. `CLAUDE.md` points here
- `docs/context/01-project.md`: pitch, users, scope
- `docs/context/02-assignment-rules.md`: hard constraints
- `docs/context/03-architecture.md`: files, env vars, routes
- `docs/context/04-data-model.md`: SQLite tables
- `docs/context/05-logic-spec.md`: strategy, settlement, scoring, Jev questions
- `docs/context/06-commit-plan.md`: what each commit contains
- `docs/context/07-learning-guide.md`: explain-back questions
