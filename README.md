# ACI606 — Docker Rescue Challenge

Aplicación web multi-servicio ejecutada con Docker Compose, recibida con fallas, diagnosticada y reparada.

```
Navegador ──► frontend (Nginx :80, publicado en ${FRONTEND_PORT:-8080})
                 │  /api/*  →  proxy
                 ▼
              backend (FastAPI/uvicorn :8000)
                 │  SQLAlchemy + psycopg2
                 ▼
              db (PostgreSQL 16 :5432) ── volumen nombrado aci606-rescue_pgdata
```

Integrantes: José Molina, Christopher Villalobos, Samantha Rojo — ACI606 Cloud Computing, UDLA.

---

## 1. Requisitos

| Herramienta | Versión probada | Comprobar con |
|---|---|---|
| Docker Engine | 29.x | `docker --version` |
| Docker Compose (plugin v2) | v5.x | `docker compose version` |
| curl (para verificar) | cualquiera | `curl --version` |

También funciona en **GitHub Codespaces** (Docker ya viene instalado).

## 2. Configuración

Todos los valores tienen un **valor por defecto** en `compose.yaml`, así que un clon limpio funciona **sin crear `.env`**.
Para cambiarlos:

```bash
cp .env.example .env     # .env está en .gitignore: nunca se versiona
# editar .env
```

| Variable | Por defecto | Uso |
|---|---|---|
| `FRONTEND_PORT` | `8080` | Puerto del host que se publica hacia el puerto 80 de Nginx |
| `POSTGRES_USER` | `appuser` | Usuario de PostgreSQL; también se usa para armar `DATABASE_URL` del backend |
| `POSTGRES_PASSWORD` | `rescue123` | Contraseña de PostgreSQL; también se usa en `DATABASE_URL` |
| `POSTGRES_DB` | `appdb` | Base de datos; también se usa en `DATABASE_URL` |

Variables internas (definidas en `compose.yaml`, normalmente no se cambian):

| Variable | Servicio | Valor |
|---|---|---|
| `DATABASE_URL` | backend | `postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}`. Es obligatoria: si falta, el backend termina con `RuntimeError` |
| `BACKEND_HOST` / `BACKEND_PORT` | frontend | `backend` / `8000` (destino del proxy `/api/`) |

> **Importante:** `POSTGRES_*` solo se aplican cuando PostgreSQL inicializa un volumen **vacío**. Si ya existe
> `aci606-rescue_pgdata`, cambiar `POSTGRES_PASSWORD` en `.env` **no** cambia la contraseña guardada y el backend fallará
> con `password authentication failed`. Cámbiela también dentro de la base de datos:
> `docker compose exec db psql -U appuser -d appdb -c "ALTER USER appuser PASSWORD 'nueva';"`

## 3. Construir e iniciar

Desde la **raíz** del repositorio:

```bash
docker compose up --build -d
docker compose ps
```

El orden de arranque lo controlan los healthchecks: `db` (healthy, con `pg_isready`) → `backend` (healthy, con `GET /health`) → `frontend`.
En unos 20–30 s los tres servicios deben figurar `(healthy)`:

```
NAME                       SERVICE    STATUS                    PORTS
aci606-rescue-backend-1    backend    Up ... (healthy)          8000/tcp
aci606-rescue-db-1         db         Up ... (healthy)          5432/tcp
aci606-rescue-frontend-1   frontend   Up ... (healthy)          0.0.0.0:8080->80/tcp
```

Abra http://localhost:8080 (en Codespaces: pestaña **Ports** → 8080).

## 4. Verificar

Prueba automática (frontend, `/api/health`, crear, listar y validar registros):

```bash
./scripts/smoke_test.sh                  # pruebas funcionales
./scripts/smoke_test.sh --persistencia   # además recrea los contenedores y verifica que los datos sigan
```

O manualmente:

```bash
# Página estática
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/          # 200

# API a través del proxy de Nginx
curl -s http://localhost:8080/api/health
# {"status":"ok","database":"reachable"}

# Crear y listar registros
curl -s -X POST http://localhost:8080/api/items \
     -H "Content-Type: application/json" -d '{"name":"mi registro"}'
curl -s http://localhost:8080/api/items

# Consultar directamente la base de datos
docker compose exec db psql -U appuser -d appdb -c "SELECT * FROM items;"

# Estado de salud detallado
docker inspect --format '{{json .State.Health}}' aci606-rescue-backend-1
```

## 5. Detener

```bash
docker compose stop      # detiene los contenedores; se reanudan con: docker compose start
docker compose down      # elimina contenedores y red; el volumen de datos se CONSERVA
```

> ⚠️ **`docker compose down -v` borra el volumen `aci606-rescue_pgdata` y con él todos los datos.**
> Úselo solo si quiere reiniciar la base de datos desde cero.

## 6. Recrear comprobando persistencia

```bash
curl -s -X POST http://localhost:8080/api/items -H "Content-Type: application/json" -d '{"name":"persistencia"}'
docker compose down
docker compose up -d
curl -s http://localhost:8080/api/items          # el registro "persistencia" sigue ahí
docker volume inspect aci606-rescue_pgdata
```

## 7. Diagnóstico

| Síntoma | Qué revisar |
|---|---|
| Un servicio no figura `healthy` | `docker compose ps -a` · `docker compose logs <servicio>` · `docker inspect --format '{{json .State.Health}}' aci606-rescue-<servicio>-1` |
| `/api/...` responde **502** | El backend está detenido o no resuelve: `docker compose ps backend`, `docker compose logs frontend \| grep error` |
| `/api/...` responde **503** | El backend funciona pero no alcanza PostgreSQL: `docker compose ps db`, `docker compose logs db` |
| `password authentication failed` | `.env` y la contraseña guardada en el volumen no coinciden (ver nota de la sección 2) |
| `RuntimeError: ... DATABASE_URL no está definida` | El backend arrancó sin `DATABASE_URL`: `docker compose config \| grep DATABASE_URL` |
| No responde en el puerto del host | `docker compose ps frontend` (columna PORTS) y `FRONTEND_PORT` en `.env` |
| Ver la config real de Nginx | `docker compose exec frontend cat /etc/nginx/conf.d/default.conf` |
| Configuración final de Compose | `docker compose config` |

Todos los servicios usan `restart: unless-stopped`. Esta política reinicia un contenedor
cuando termina su proceso, pero no cuando solamente cambia a estado `unhealthy`.
Al detener PostgreSQL, el healthcheck del backend falla y,
cuando se inicia nuevamente la base de datos, el mismo backend vuelve a `healthy`
sin reiniciarse (RestartCount=0 y mismo StartedAt).
Nginx resuelve `backend` en cada petición, así que no necesita reiniciarse si el backend se recrea.

## 8. Estructura

```
.
├── backend/
│   ├── Dockerfile            # python:3.12-slim + uvicorn main:app, sin root
│   ├── main.py               # API FastAPI: /health, /items
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile            # nginx:1.27-alpine; nginx.conf como plantilla envsubst
│   ├── index.html
│   └── nginx.conf            # proxy /api/ → ${BACKEND_HOST}:${BACKEND_PORT} + cabeceras de seguridad
├── scripts/
│   └── smoke_test.sh         # prueba rápida de extremo a extremo
├── .dockerignore
├── .env.example              # plantilla de configuración (copiar a .env)
├── .gitignore
├── README.md
└── compose.yaml              # servicios, healthchecks, red app_net, volumen pgdata
```
