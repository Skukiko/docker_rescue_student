#!/usr/bin/env bash
# Prueba de extremo a extremo: frontend -> Nginx -> FastAPI -> PostgreSQL.
#
# Uso (desde la raíz, con los servicios levantados):
#   ./scripts/smoke_test.sh                 pruebas funcionales
#   ./scripts/smoke_test.sh --persistencia  además recrea los contenedores y
#                                           comprueba que el registro sigue ahí
set -euo pipefail
cd "$(dirname "$0")/.."

BASE_URL="${BASE_URL:-http://localhost:8080}"
NAME="smoke-$(date +%s)"

ok()   { printf '  \033[32m✔\033[0m %s\n' "$*"; }
fail() { printf '  \033[31m✘ %s\033[0m\n' "$*" >&2; exit 1; }
json() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }

echo "Probando $BASE_URL"

code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/")
[[ "$code" == 200 ]] && ok "Frontend responde 200" || fail "Frontend respondió $code"

health=$(curl -sf "$BASE_URL/api/health") || fail "/api/health no responde 200"
echo "$health" | json 'assert d=={"status":"ok","database":"reachable"}, d' \
  && ok "Backend y PostgreSQL: $health" || fail "/api/health: $health"

created=$(curl -sf -X POST "$BASE_URL/api/items" \
  -H 'Content-Type: application/json' -d "{\"name\":\"$NAME\"}") || fail "POST /api/items"
id=$(echo "$created" | json 'print(d["id"])')
ok "Registro creado (id $id)"

has_item() { curl -sf "$BASE_URL/api/items" | json "assert any(i['id']==$id for i in d)"; }
has_item && ok "El registro aparece en GET /api/items" || fail "El registro $id no aparece"

code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE_URL/api/items" \
  -H 'Content-Type: application/json' -d '{"name":""}')
[[ "$code" == 422 ]] && ok "Nombre vacío rechazado (422)" || fail "Nombre vacío devolvió $code"

if [[ "${1:-}" == "--persistencia" ]]; then
  echo "Recreando contenedores (docker compose down / up)..."
  docker compose down >/dev/null 2>&1
  docker compose up -d --wait >/dev/null 2>&1 || fail "Los servicios no quedaron healthy"
  has_item && ok "El registro $id sobrevivió a down/up" || fail "Se perdió el registro $id"
fi

echo "OK: todas las pruebas pasaron"
