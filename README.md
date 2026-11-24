# ACI606 Docker Rescue Challenge

Evaluación 2 de ACI606 Especialidad II: Cloud Computing (UDLA, sección 401).
Integrantes: José Molina, Christopher Villalobos y Samantha Rojo.

Recibimos una aplicación de tres servicios (Nginx, FastAPI y PostgreSQL) que no funcionaba. El backend se caía al
partir, la página no respondía en el puerto 8080 y los datos se perdían al recrear los contenedores. En este
repositorio está la versión reparada. El detalle de cada falla, con su evidencia, está en el informe técnico que
entregamos aparte.

Para levantarla basta con:

```bash
docker compose up --build -d
docker compose ps
```

Después de unos 30 segundos los tres servicios deberían aparecer como `(healthy)` y la aplicación queda en
http://localhost:8080.

## Arquitectura

```mermaid
flowchart LR
    nav(["Navegador"]) -- "host :8080 → :80" --> fe
    subgraph net["red app_net"]
        fe["③ frontend<br/>Nginx :80<br/>healthcheck: wget /"]
        be["② backend<br/>FastAPI :8000<br/>healthcheck: GET /health"]
        db[("① db<br/>PostgreSQL :5432<br/>healthcheck: pg_isready")]
    end
    fe -- "/api/* → backend:8000/*" --> be
    be -- "db:5432 (service_healthy)" --> db
    db --- vol[/"volumen nombrado<br/>aci606-rescue_pgdata"/]
    env{{".env (opcional)<br/>POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB"}} -.-> be
    env -.-> db
```

Nginx sirve la página y reenvía todo lo que llega a `/api/` al backend, quitándole ese prefijo. El backend guarda
los registros en PostgreSQL. Solo el frontend publica un puerto en el host (el 8080); el backend y la base de datos
quedan dentro de la red `app_net` y se encuentran por su nombre de servicio, nunca por `localhost`, que dentro de
un contenedor apunta al mismo contenedor. Ese error estaba dos veces en el paquete original.

Los servicios parten en orden gracias a los healthchecks: primero `db`, cuando acepta conexiones parte `backend`, y
cuando el backend responde `/health` parte `frontend`. Los datos quedan en el volumen `aci606-rescue_pgdata`, que no
se borra con `docker compose down`.

| Servicio | Imagen | Puerto | Healthcheck |
|---|---|---|---|
| frontend | nginx:1.27-alpine (build) | 8080 en el host → 80 | `wget /` |
| backend | python:3.12-slim (build) | 8000, solo interno | `GET /health` (hace un `SELECT 1`) |
| db | postgres:16-alpine | 5432, solo interno | `pg_isready` |

## Requisitos

Docker y el plugin Docker Compose v2 (`docker --version` y `docker compose version` para revisar), además de curl
para las pruebas. En GitHub Codespaces funciona directo: el archivo
[.devcontainer/devcontainer.json](.devcontainer/devcontainer.json) usa una imagen que ya trae Docker y reenvía el
puerto 8080.

## Configuración

No hace falta crear nada. Las credenciales de PostgreSQL tienen valores por defecto en `compose.yaml`, así que un
clon recién descargado funciona tal cual. Si se quieren cambiar:

```bash
cp .env.example .env
```

| Variable | Por defecto |
|---|---|
| `POSTGRES_USER` | `appuser` |
| `POSTGRES_PASSWORD` | `rescue123` |
| `POSTGRES_DB` | `appdb` |

Con estas tres variables se arma también la `DATABASE_URL` del backend, por lo que la contraseña siempre coincide en
los dos lados (justo lo que fallaba en el paquete original). El archivo `.env` está en `.gitignore`.

Hay un detalle que nos costó entender: PostgreSQL usa estas variables solo la primera vez, cuando el volumen está
vacío. Si el volumen ya existe y se cambia `POSTGRES_PASSWORD`, el backend deja de conectarse. En ese caso hay que
cambiar la contraseña también dentro de la base:

```bash
docker compose exec db psql -U appuser -d appdb -c "ALTER USER appuser PASSWORD 'nueva';"
```

## Iniciar y revisar

Desde la raíz del repositorio:

```bash
docker compose config -q && echo "compose.yaml válido"
docker compose up --build -d
docker compose ps
```

Lo esperado es algo así:

```
NAME                       SERVICE    STATUS                    PORTS
aci606-rescue-backend-1    backend    Up ... (healthy)          8000/tcp
aci606-rescue-db-1         db         Up ... (healthy)          5432/tcp
aci606-rescue-frontend-1   frontend   Up ... (healthy)          0.0.0.0:8080->80/tcp
```

En el navegador, http://localhost:8080 debería mostrar `Backend: ok | DB: reachable` y dejar agregar registros (en
Codespaces se abre desde la pestaña Ports).

Para probar todo de una vez dejamos un script:

```bash
./scripts/smoke_test.sh                  # página, /api/health, crear, listar y rechazar un nombre vacío
./scripts/smoke_test.sh --persistencia   # lo mismo, y además recrea los contenedores y revisa que el dato siga
```

También se puede revisar a mano:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/      # 200
curl -s http://localhost:8080/api/health                               # {"status":"ok","database":"reachable"}
curl -s -X POST http://localhost:8080/api/items \
     -H "Content-Type: application/json" -d '{"name":"mi registro"}'   # 201
curl -s http://localhost:8080/api/items
docker compose exec db psql -U appuser -d appdb -c "SELECT * FROM items;"
```

La API tiene dos rutas: `/api/health`, que responde 200 si la API y la base están bien y 503 si la base no
responde, y `/api/items`, que lista con GET y crea con POST (`{"name": "..."}`, entre 1 y 80 caracteres).

## Detener y recrear

```bash
docker compose stop            # detiene; se vuelve a levantar con docker compose start
docker compose down            # borra contenedores y red, pero el volumen con los datos se queda
docker compose up --build -d   # vuelve a crear todo y los registros siguen ahí
```

Ojo con `docker compose down -v`: el `-v` borra el volumen y con él toda la base de datos. Solo sirve si se quiere
partir de cero.

## Pruebas de la pauta (P1 a P6)

Así hicimos las seis pruebas obligatorias. Conviene correrlas en este orden.

| Prueba | Comandos | Qué debería pasar |
|---|---|---|
| P1 Arranque limpio | `docker compose down`<br/>`docker compose up --build -d`<br/>`docker compose ps` | Parten db, backend y frontend, en ese orden, y los tres quedan `(healthy)` |
| P2 Comunicación | `curl -s http://localhost:8080/api/health`<br/>`curl -s -X POST http://localhost:8080/api/items -H "Content-Type: application/json" -d '{"name":"prueba P2"}'`<br/>`docker compose exec db psql -U appuser -d appdb -c "SELECT * FROM items;"` | `reachable`, luego `201`, y el registro aparece en PostgreSQL |
| P3 Persistencia | `docker compose down && docker compose up -d`<br/>`docker compose up -d --force-recreate db`<br/>`curl -s http://localhost:8080/api/items` | El registro de P2 sigue después de las dos recreaciones |
| P4 Fallo controlado | `docker compose stop db`<br/>`curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/`<br/>`curl -s -w " %{http_code}\n" http://localhost:8080/api/items` | La página sigue cargando (200), pero la API responde `503 database unavailable` |
| P5 Diagnóstico | `docker compose ps`<br/>`docker compose logs --tail=20 backend`<br/>`docker inspect --format '{{json .State.Health}}' aci606-rescue-backend-1` | El backend pasa a `(unhealthy)` y el log dice la causa: `could not translate host name "db"` |
| P6 Recuperación | `docker compose start db`<br/>(esperar unos 30 s)<br/>`docker compose ps`<br/>`curl -s http://localhost:8080/api/health` | Los tres vuelven a `(healthy)` sin reiniciar el backend, y los datos están intactos |

## Si algo falla

Lo primero que revisamos siempre fue `docker compose ps -a` y después los logs del servicio con problemas
(`docker compose logs <servicio>`). Algunos casos que nos tocaron:

| Síntoma | Qué mirar |
|---|---|
| Un servicio no llega a `healthy` | `docker inspect --format '{{json .State.Health}}' aci606-rescue-<servicio>-1` |
| La API responde 502 | El backend está caído o Nginx no lo encuentra: `docker compose ps backend` y `docker compose logs frontend` |
| La API responde 503 | El backend está bien pero no llega a PostgreSQL: `docker compose ps db` y `docker compose logs db` |
| `password authentication failed` | La contraseña de `.env` no es la que tiene guardada el volumen (ver Configuración) |
| No abre http://localhost:8080 | En `docker compose ps frontend` la columna PORTS debe mostrar `0.0.0.0:8080->80/tcp` |
| Ver la configuración real | `docker compose config` y `docker compose exec frontend cat /etc/nginx/conf.d/default.conf` |
| Red y volumen | `docker network inspect aci606-rescue_app_net` y `docker volume inspect aci606-rescue_pgdata` |

Si se detiene la base de datos, el backend queda `unhealthy` pero no se reinicia (la política `unless-stopped` solo
reinicia cuando el proceso termina). Cuando la base vuelve, el mismo backend se recupera solo. Nginx busca al
backend por nombre en cada petición, así que tampoco hay que reiniciarlo si el backend se recrea.

## Qué reparamos

Cada fila es un commit del historial (`git log --oneline --reverse`). Las fallas aparecían en cascada: al arreglar
una, el mismo log mostraba la siguiente, por eso fuimos de a una.

| | Problema | Cómo lo arreglamos | Commit |
|---|---|---|---|
| R-01 | El backend terminaba con `Exited (1)` porque uvicorn buscaba un módulo `app` que no existe | El `CMD` apunta a `main:app` | [`6153037`](https://github.com/Skukiko/docker_rescue_student/commit/6153037be0f88dec1078806d5c3ba591e404e573) |
| R-02 | `ModuleNotFoundError: psycopg2`, faltaba el driver de PostgreSQL | Agregamos `psycopg2-binary==2.9.10` a `requirements.txt` | [`5e08230`](https://github.com/Skukiko/docker_rescue_student/commit/5e0823046d34fbcbbeb797ed65ed6c095b25a484) |
| R-03 | La `DATABASE_URL` usaba `localhost`, que para el backend es él mismo | Usamos el host `db`, el nombre del servicio | [`5bf2ad3`](https://github.com/Skukiko/docker_rescue_student/commit/5bf2ad3e93cffa92656fbc47cf2df30941ea3653) |
| R-04 | `password authentication failed`, la URL tenía `wrongpass` | La misma contraseña que `POSTGRES_PASSWORD` | [`c3401b4`](https://github.com/Skukiko/docker_rescue_student/commit/c3401b498d8b66ad4e621ac326a6e5c6f128a0dd) |
| R-05 | El backend no esperaba a que PostgreSQL aceptara conexiones | Healthcheck con `pg_isready` y `condition: service_healthy` | [`88d3387`](https://github.com/Skukiko/docker_rescue_student/commit/88d3387c84e3edc9876651b6c7f8ec8860641cfd) |
| R-06 | El frontend estaba `Up` pero no respondía: se publicaba `8080:8080` y Nginx escucha en el 80 | Cambiamos a `8080:80` | [`d611282`](https://github.com/Skukiko/docker_rescue_student/commit/d6112829dfbd518ff1aa5e8a206e88f385fafda7) |
| R-07 | `502 Bad Gateway`, Nginx mandaba `/api/` a `localhost:8000` | `proxy_pass` hacia `backend:8000` | [`64d44c9`](https://github.com/Skukiko/docker_rescue_student/commit/64d44c96c9f889356d80e014353fe2fecd91c01c) |
| R-08 | Los datos se perdían con `down` y `up` porque la base usaba un volumen anónimo | Volumen nombrado `pgdata` | [`e721a7e`](https://github.com/Skukiko/docker_rescue_student/commit/e721a7e70ffa3da6e5195d577d0f9cfc1fa0f924) |
| M-01 | Credenciales escritas en varios lugares y una URL con contraseña dentro del código | Variables con valores por defecto y `.env.example` | [`45ceef1`](https://github.com/Skukiko/docker_rescue_student/commit/45ceef1409844cb8eac74106c4cbf7cca037a014) |
| M-02 | Un contenedor `Up` no significa que funcione | Healthchecks en backend y frontend, `restart` y red `app_net` | [`9b4747c`](https://github.com/Skukiko/docker_rescue_student/commit/9b4747ce9334ff49cd3754a9235f2456ce389a24) |
| M-03 | Si el backend no existía, Nginx no partía | Nginx resuelve el nombre del backend en cada petición | [`9ccc0ae`](https://github.com/Skukiko/docker_rescue_student/commit/9ccc0ae8cba5cd3b4f059f78983830ea63aaa5b2) |
| M-04 | No había instrucciones para reproducirlo | Este README y `devcontainer.json` | [`888a2e3`](https://github.com/Skukiko/docker_rescue_student/commit/888a2e3035828089ca495e4f866dd7009a90030e) |
| M-05 | Con la base caída la API respondía 500 con el error interno, el backend corría como root y Nginx mostraba su versión | 503 en toda la API, usuario sin privilegios, `server_tokens off`, cabeceras de seguridad y el script de prueba | [`c729fb6`](https://github.com/Skukiko/docker_rescue_student/commit/c729fb6a22b60b20ffb749c3d67b1314f3f30790) · [`9df96f2`](https://github.com/Skukiko/docker_rescue_student/commit/9df96f2efe6b7baf1ac4543c9972e496de7e54f9) · [`6bbc079`](https://github.com/Skukiko/docker_rescue_student/commit/6bbc07973a79d89cb96945d8ae6bab99edb8673b) |

## Archivos

```
.
├── compose.yaml                     servicios, healthchecks, red app_net y volumen pgdata
├── .env.example                     plantilla de configuración (se copia a .env)
├── .gitignore
├── .devcontainer/devcontainer.json  Codespaces con Docker y el puerto 8080
├── backend/
│   ├── Dockerfile                   python:3.12-slim, uvicorn main:app, usuario sin privilegios
│   ├── .dockerignore
│   ├── main.py                      API en FastAPI: /health y /items
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile                   nginx:1.27-alpine, nginx.conf como plantilla
│   ├── .dockerignore
│   ├── index.html
│   └── nginx.conf                   proxy de /api/ al backend y cabeceras de seguridad
└── scripts/smoke_test.sh            prueba de punta a punta (con --persistencia recrea los contenedores)
```
