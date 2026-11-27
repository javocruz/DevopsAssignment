#!/usr/bin/env bash
# Run in the main-branch CD job after azure/login and both SHA-tagged image pushes.
set -euo pipefail
: "${PREFIX:?}" "${RESOURCE_GROUP:?}" "${UI_STORAGE:?}" "${GITHUB_SHA:?}"
: "${GITHUB_REPOSITORY_OWNER:?}" "${BOOK_DB_PASSWORD:?}" "${INTEL_DB_PASSWORD:?}" "${ADMIN_TOKEN:?}"

owner=$(printf '%s' "$GITHUB_REPOSITORY_OWNER" | tr '[:upper:]' '[:lower:]')
origin=$(az storage account show -g "$RESOURCE_GROUP" -n "$UI_STORAGE" --query primaryEndpoints.web -o tsv)
origin=${origin%/}
host_for() {
    az containerapp show -g "$RESOURCE_GROUP" -n "$PREFIX-$1" --query properties.configuration.ingress.fqdn -o tsv
}
intel_url="https://$(host_for intel)"
book_url="https://$(host_for book)"

for service in intel book; do
    password=$INTEL_DB_PASSWORD
    extra=()
    if [[ $service == book ]]; then
        password=$BOOK_DB_PASSWORD
        extra+=("INTEL_URL=$intel_url")
    fi
    app="$PREFIX-$service"
    az containerapp secret set -g "$RESOURCE_GROUP" -n "$app" \
        --secrets "db-password=$password" "admin-token=$ADMIN_TOKEN" -o none
    az containerapp update -g "$RESOURCE_GROUP" -n "$app" \
        --image "ghcr.io/$owner/$app:$GITHUB_SHA" \
        --set-env-vars "GIT_SHA=$GITHUB_SHA" "CORS_ORIGINS=$origin" \
        "DATABASE_URL=mssql://$service@$PREFIX-sql.database.windows.net:1433/$app-db" \
        "DB_PASSWORD=secretref:db-password" "ADMIN_TOKEN=secretref:admin-token" "${extra[@]}" -o none
done

for url in "$intel_url" "$book_url"; do
    deadline=$((SECONDS + 300))
    until curl -fsS --max-time 12 "$url/health" | python3 -c '
import json, os, sys
body = json.load(sys.stdin)
sys.exit(0 if body == {"status": "ok", "db": "ok", "version": os.environ["GITHUB_SHA"]} else 1)
'; do
        if (( SECONDS >= deadline )); then echo "Health check failed: $url" >&2; exit 1; fi
        sleep 5
    done
done

python3 - "$intel_url" "$book_url" <<'PYCONFIG'
import json
import sys
from pathlib import Path

config = {"intelUrl": sys.argv[1], "bookUrl": sys.argv[2]}
Path("ui/config.js").write_text("window.EDGEBOOK_CONFIG = " + json.dumps(config) + ";\n")
PYCONFIG
az storage blob upload-batch --auth-mode login --account-name "$UI_STORAGE" \
    --destination '$web' --source ui --overwrite -o none
