#!/usr/bin/env bash
set -euo pipefail
sqlcmd=/opt/mssql-tools18/bin/sqlcmd
export SQLCMDPASSWORD="$MSSQL_SA_PASSWORD"
rm -f /tmp/edgebook-db-ready
/opt/mssql/bin/sqlservr &
pid=$!
trap 'kill -TERM "$pid" 2>/dev/null || true' EXIT TERM INT

until "$sqlcmd" -S localhost -U sa -C -l 2 -Q 'SELECT 1' >/dev/null 2>&1; do
    kill -0 "$pid" || exit 1
    sleep 2
done

initialize() {
    # Pass SQL Server Unicode bytes as hex so punctuation stays inside the password.
    export DatabaseName="$1"
    PasswordHex=$(printf '%s' "$2" | iconv -f UTF-8 -t UTF-16LE | od -An -v -tx1 | tr -d ' \n')
    export PasswordHex
    "$sqlcmd" -S localhost -U sa -C -b -i /bootstrap/init.sql
}

initialize intel "$INTEL_DB_PASSWORD"
initialize book "$BOOK_DB_PASSWORD"
touch /tmp/edgebook-db-ready
wait "$pid"
