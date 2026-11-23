#!/usr/bin/env bash
# Prueba rápida: verifica frontend, API (vía proxy Nginx) y base de datos.
# Uso: ./scripts/smoke_test.sh   (con los servicios levantados: docker compose up --build -d)
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:${FRONTEND_PORT:-8080}}"
fail() { echo "FALLO: $*" >&2; exit 1; }

echo "1) Frontend en $BASE_URL/"
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE_URL/")
[ "$code" = "200" ] || fail "frontend respondió $code"

echo "2) Salud del backend y la base de datos"
health=$(curl -s "$BASE_URL/api/health")
echo "$health" | grep -q '"reachable"' || fail "/api/health: $health"

echo "3) Crear un registro"
name="smoke-$(date +%s)"
curl -s -f -X POST "$BASE_URL/api/items" \
     -H 'Content-Type: application/json' -d "{\"name\":\"$name\"}" > /dev/null || fail "POST /api/items"

echo "4) Listar registros"
curl -s -f "$BASE_URL/api/items" | grep -q "$name" || fail "el registro $name no aparece"

echo "OK: todas las pruebas pasaron"
