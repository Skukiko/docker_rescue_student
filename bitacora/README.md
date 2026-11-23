# Bitácora de reparaciones — ACI606 Docker Rescue Challenge

Integrantes: José Molina, Christopher Villalobos, Samantha Rojo.

Cada ficha sigue la secuencia **síntoma → evidencia → causa raíz → corrección → verificación**. Las salidas
reales de los comandos están en [`../evidencias/`](../evidencias/). El paquete recibido, sin modificar, está en [`original/`](original/).

## Preparación

| Paso | Descripción | Commit |
|---|---|---|
| 0 | Proyecto movido de `docker_rescue_student/` a la raíz (sin cambios de contenido; desde la raíz `docker compose config` daba `no configuration file provided: not found`, ver `evidencias/00_*`) | `fe127cc` |
| 0 | Copia de referencia de los 8 archivos originales en `bitacora/original/` | `34c0313` |
| 1 | Diagnóstico inicial: `evidencias/01_*.txt` (incluido en el commit de R-01) | `748f5c2` |

## Incidencias

| ID | Síntoma | Causa raíz | Archivo modificado | Commit |
|---|---|---|---|---|
| [R-01](R-01.md) | Backend `Exited (1)`: `Could not import module "app"` | `CMD` usa `app:app`; el código está en `main.py` | `backend/Dockerfile` | `748f5c2` |
| [R-02](R-02.md) | `ModuleNotFoundError: No module named 'psycopg2'` | SQLAlchemy necesita un driver de PostgreSQL que no estaba en las dependencias | `backend/requirements.txt` | `ba9a7ac` |
| [R-03](R-03.md) | `connection to server at "localhost" ... 5432 failed: Connection refused` | Dentro del contenedor, `localhost` es el propio backend; la base de datos es el servicio `db` | `compose.yaml` | `bcfbc91` |
| [R-04](R-04.md) | `FATAL: password authentication failed for user "appuser"` (backend y db) | `DATABASE_URL` usa `wrongpass`; `POSTGRES_PASSWORD` es `rescue123` | `compose.yaml` | `5aa17c9` |
| [R-05](R-05.md) | Con db no disponible, el backend queda `Exited (3)` y no se recupera | `depends_on` simple = `service_started`; sin healthcheck ni reinicio | `compose.yaml` | `25a69c5` |
| [R-06](R-06.md) | Frontend `Up`, pero `curl :8080` → `Connection reset by peer` | Se publica `8080:8080`; Nginx escucha en el 80 | `compose.yaml` | `e6f1716` |
| [R-07](R-07.md) | `/api/health` → `502`; Nginx: upstream `127.0.0.1:8000` / `[::1]:8000` | `proxy_pass` a `localhost`, que es el propio contenedor de Nginx | `frontend/nginx.conf` | `89ebb3a` |
| [R-08](R-08.md) | Tras `down` + `up`, `GET /api/items` → `[]` | Datos en un volumen anónimo nuevo en cada contenedor | `compose.yaml` | `8f3588f` |

## Mejoras

| ID | Problema | Mejora | Archivos | Commit |
|---|---|---|---|---|
| [M-01](M-01.md) | Credenciales duplicadas y una URL con contraseña por defecto en el código | Variables `${VAR:-default}`, `.env.example`, `.gitignore`, `.dockerignore`; `RuntimeError` si falta `DATABASE_URL` | `compose.yaml`, `backend/main.py`, `.env.example`, `.gitignore`, `backend/.dockerignore`, `frontend/.dockerignore` | `8fb287f` |
| [M-02](M-02.md) | "Up" ≠ sano; sin reinicio automático | Healthchecks de backend (Python) y frontend (wget), `restart: unless-stopped`, red `app_net`, `PYTHONUNBUFFERED`/`PYTHONDONTWRITEBYTECODE` | `compose.yaml`, `backend/Dockerfile` | `af9fff7` |
| [M-03](M-03.md) | Con el backend detenido, Nginx no arranca (`host not found in upstream`) y entra en bucle | `resolver 127.0.0.11`, destino por variables `BACKEND_HOST`/`BACKEND_PORT` vía plantilla envsubst | `frontend/nginx.conf`, `frontend/Dockerfile`, `compose.yaml` | `bd818be` |
| [M-04](M-04.md) | Sin documentación operativa | README reproducible, `docs/arquitectura.md` (mermaid inicial y final), `.devcontainer/devcontainer.json` | `README.md`, `docs/arquitectura.md`, `.devcontainer/devcontainer.json` | `4b36d62` |
| [M-05](M-05.md) | `GET /items` → 500 con la base de datos caída; `/health` expone el error interno; APIs obsoletas; backend como `root`; Nginx revela su versión | Manejador global de `OperationalError` (503), `lifespan`, `USER appuser`, `server_tokens off` y cabeceras de seguridad, `maxlength=80`, `scripts/smoke_test.sh` | `backend/main.py`, `backend/Dockerfile`, `frontend/nginx.conf`, `frontend/index.html`, `scripts/smoke_test.sh` | `8ab6044`, `6386c32`, `f8cb8a9` |

## Pruebas de validación (commit `768d438`)

| Prueba | Qué se comprobó | Resultado | Evidencia |
|---|---|---|---|
| P1 Arranque limpio | `down` → `up --build -d`: db Healthy → backend Healthy → frontend; los 3 `(healthy)` | ✅ OK | [P1](../evidencias/P1_arranque_limpio.txt) |
| P2 Comunicación | `/api/health` 200 `reachable`; `POST /api/items` 201 (id 3); `SELECT * FROM items` en psql muestra 3 filas | ✅ OK | [P2](../evidencias/P2_comunicacion.txt) |
| P3 Persistencia | `down` + `up -d` y `up -d --force-recreate db` (nuevo id de contenedor): los 3 registros permanecen | ✅ OK | [P3](../evidencias/P3_persistencia.txt) |
| P4 Fallo controlado | `stop db` + 60 s: frontend `/` 200, `/api/health` 503, backend `(unhealthy)` | ✅ OK | [P4](../evidencias/P4_fallo_controlado.txt) |
| P5 Diagnóstico | Logs del backend con `GET /health 503`; `.State.Health` = `unhealthy`, `FailingStreak: 6`, `HTTP Error 503` | ✅ OK | [P5](../evidencias/P5_diagnostico.txt) |
| P6 Recuperación | `start db` + 35 s: los 3 `(healthy)`, `/api/health` 200, datos intactos; el backend se recuperó **sin reiniciarse** (`RestartCount=0`, mismo `StartedAt`) | ✅ OK | [P6](../evidencias/P6_recuperacion.txt) |

## Diferencias respecto de lo esperado

- **R-02 → R-03:** desde R-02 en adelante el backend termina con `Exited (3)` y no `(1)`: uvicorn usa el 3 cuando falla el evento `startup`.
- **R-06:** el síntoma fue `Recv failure: Connection reset by peer` (una de las dos variantes previstas).
- **R-07:** el log de Nginx muestra el upstream tanto como `127.0.0.1:8000` como `[::1]:8000` (4 veces cada uno), porque `localhost` resuelve a IPv4 e IPv6.
- **R-08:** el volumen nombrado empezó vacío; el registro de R-07 quedó en un volumen anónimo antiguo. Quedan 3 volúmenes anónimos huérfanos sin borrar.
- **M-02:** la red anterior `aci606-rescue_default` quedó huérfana (sin contenedores), porque `down` ya no la gestiona.
- **M-03:** el efecto fue más grave que lo previsto: Nginx no solo falla, sino que entra en bucle `Restarting (1)` y deja caída también la página estática.
