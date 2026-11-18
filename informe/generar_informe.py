#!/usr/bin/env python3
"""Genera informe/Informe_Tecnico_ACI606_Evaluacion2.docx.
Fuentes: bitacora/*.md, evidencias/*.txt (vía informe/img), git log, archivos finales del repositorio.
Uso: python3 informe/generar_informe.py   (desde la raíz; antes ejecutar generar_imagenes.py)
"""
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "informe" / "img"
OUT = ROOT / "informe" / "Informe_Tecnico_ACI606_Evaluacion2.docx"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


REPO = git("remote", "get-url", "origin").removesuffix(".git")
if REPO.startswith("git@github.com:"):
    REPO = "https://github.com/" + REPO.split(":", 1)[1]
COMMITS = [l.split("|", 1) for l in git("log", "--reverse", "--format=%h|%s").splitlines()]
HASH = {}
for h, msg in COMMITS:
    for tag in ["R-0%d" % i for i in range(1, 9)] + ["M-0%d" % i for i in range(1, 5)]:
        if f"({tag})" in msg:
            HASH[tag] = (h, msg)

doc = Document()
FONT = "Liberation Sans"

# ------------------------------------------------------------------ estilos y página
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, side, Cm(2.5))

st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(3)
st.paragraph_format.line_spacing = 1.0
for name, size in (("Heading 1", 14), ("Heading 2", 12), ("Title", 22)):
    s = doc.styles[name]
    s.font.name = FONT
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.color.rgb = RGBColor(0x1F, 0x2D, 0x3D)
    s.element.rPr.rFonts.set(qn("w:ascii"), FONT)
    s.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
doc.styles["Heading 1"].paragraph_format.space_before = Pt(12)
doc.styles["Heading 1"].paragraph_format.space_after = Pt(4)
doc.styles["Heading 2"].paragraph_format.space_before = Pt(8)
doc.styles["Heading 2"].paragraph_format.space_after = Pt(3)

cap = doc.styles["Caption"]
cap.font.name = FONT
cap.font.size = Pt(9)
cap.font.italic = True
cap.font.color.rgb = RGBColor(0x40, 0x40, 0x40)
cap.paragraph_format.space_after = Pt(3)


def field(paragraph, instr):
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), instr)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    paragraph._p.append(fld)


# ------------------------------------------------------------------ helpers
FIG = [0]
H1 = [0]
H2 = [0]


def h1(text, numbered=True):
    if numbered:
        H1[0] += 1
        H2[0] = 0
        text = f"{H1[0]}. {text}"
    return doc.add_heading(text, level=1)


def h2(text):
    H2[0] += 1
    return doc.add_heading(f"{H1[0]}.{H2[0]} {text}", level=2)


def para(text="", bold_prefix=None, size=None, align=None, space_after=None):
    p = doc.add_paragraph()
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        if size:
            r.font.size = Pt(size)
    r = p.add_run(text)
    if size:
        r.font.size = Pt(size)
    if align:
        p.alignment = align
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    if bold_prefix:
        p.add_run(bold_prefix).bold = True
    p.add_run(text)
    p.paragraph_format.space_after = Pt(2)
    return p


def nextfig(k=1):
    return FIG[0] + k


def figure(img, caption, width_cm=14):
    FIG[0] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(1)
    p.add_run().add_picture(str(IMG / img if not str(img).startswith("/") else img), width=Cm(width_cm))
    c = doc.add_paragraph(f"Figura {FIG[0]}: {caption}", style="Caption")
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return FIG[0]


ANNEX = []


def annex(img, caption):
    """Registra una figura para los anexos y devuelve su etiqueta (A1, A2, …)."""
    ANNEX.append((img, caption))
    return f"A{len(ANNEX)}"


def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def table(header, rows, widths, size=8.5):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(size)
        shade(c, "DCE3EA")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            if isinstance(v, tuple):          # (texto, negrita)
                rr = p.add_run(v[0])
                rr.bold = v[1]
            else:
                rr = p.add_run(str(v))
            rr.font.size = Pt(size)
            p.paragraph_format.space_after = Pt(0)
    t.autofit = False
    tblPr = t._tbl.tblPr
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    tblPr.append(lay)
    for gc, w in zip(t._tbl.tblGrid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(Cm(w).twips)))
    for i, w in enumerate(widths):
        t.columns[i].width = Cm(w)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
        trp = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "true")
        trp.append(cs)
    # repetir encabezado
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def code_block(text, size=7.5):
    for line in text.rstrip("\n").split("\n"):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        r = p.add_run(line if line else " ")
        r.font.name = "DejaVu Sans Mono"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "DejaVu Sans Mono")
        r.font.size = Pt(size)


# ------------------------------------------------------------------ portada
for _ in range(4):
    doc.add_paragraph()
para("Universidad de las Américas (UDLA)", size=13, align=WD_ALIGN_PARAGRAPH.CENTER)
para("ACI606 – Especialidad II: Cloud Computing", size=13, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_paragraph()
t = doc.add_paragraph(style="Title")
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.add_run("Informe Técnico")
para("Evaluación 2 – Docker Rescue Challenge", size=16, align=WD_ALIGN_PARAGRAPH.CENTER)
para("Diagnóstico y reparación de una aplicación Docker Compose (Nginx → FastAPI → PostgreSQL)",
     size=11, align=WD_ALIGN_PARAGRAPH.CENTER)
for _ in range(3):
    doc.add_paragraph()
portada = [
    ("Docente: ", "Dr. Oscar Loyola Valenzuela"),
    ("Integrantes: ", "José Molina, Christopher Villalobos, Samantha Rojo"),
    ("Sección: ", "[SECCIÓN]"),
    ("Fecha: ", "[FECHA DE ENTREGA]"),
    ("Repositorio: ", REPO),
]
for k, v in portada:
    para(v, bold_prefix=k, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=6)

# nueva sección para el cuerpo (encabezado y pie solo desde aquí)
body = doc.add_section(WD_SECTION.NEW_PAGE)
body.different_first_page_header_footer = False
sec.different_first_page_header_footer = True
body.header.is_linked_to_previous = False
body.footer.is_linked_to_previous = False
hp = body.header.paragraphs[0]
hp.text = "ACI606 – Evaluación 2 – Docker Rescue Challenge"
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
hp.runs[0].font.size = Pt(9)
hp.runs[0].font.color.rgb = RGBColor(0x60, 0x60, 0x60)
fp = body.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
fp.add_run("Página ").font.size = Pt(9)
field(fp, "PAGE")

# ------------------------------------------------------------------ 1. Resumen ejecutivo
h1("Resumen ejecutivo")
para("El equipo recibió una aplicación de tres servicios (frontend Nginx, backend FastAPI y base de datos "
     "PostgreSQL) que no funcionaba. Con docker compose up --build -d el backend terminaba con Exited (1), el "
     "frontend figuraba Up pero no respondía en el puerto 8080 y los datos no persistían.")
para("Se identificaron ocho incidencias (R-01 a R-08), corregidas una a una y en orden, porque cada falla "
     "ocultaba a la siguiente:")
bullet("CMD con un módulo inexistente (R-01) y un driver de PostgreSQL ausente (R-02).", "Construcción: ")
bullet("URL de base de datos con localhost (R-03) y contraseña incorrecta (R-04).", "Configuración: ")
bullet("Puerto publicado mal mapeado (R-06) y proxy de Nginx hacia localhost (R-07).", "Comunicación: ")
bullet("Arranque sin espera a la base de datos (R-05) y datos en un volumen anónimo (R-08).", "Operación: ")
para("Además se aplicaron cuatro mejoras: configuración externalizada (M-01), healthchecks y reinicio "
     "automático (M-02), Nginx con resolución DNS dinámica (M-03) y documentación reproducible (M-04).")
para("Resultado: el sistema arranca desde la raíz del repositorio con docker compose up --build -d, los tres "
     "servicios quedan healthy, los datos sobreviven a down/up y a la recreación de db, y el sistema se recupera "
     "solo de una caída de la base de datos. Las seis pruebas de validación (P1 a P6) resultaron exitosas. Cada "
     "cambio tiene su commit, su ficha en bitacora/ y la salida real en evidencias/.")

# ------------------------------------------------------------------ 2. Arquitectura inicial
h1("Arquitectura inicial")
para("La Tabla 1 resume la configuración recibida (bitacora/original/compose.yaml) y el problema detectado en cada servicio.")
table(["Servicio", "Imagen", "Puerto", "Destino configurado", "Problema"], [
    ["frontend", "nginx:1.27-alpine", "8080:8080 (Nginx escucha en 80)", "proxy_pass http://localhost:8000/",
     "R-06 puerto mal mapeado; R-07 proxy a localhost"],
    ["backend", "python:3.12-slim (build)", "8000 (interno)",
     "postgresql://appuser:wrongpass@localhost:5432/appdb",
     "R-01 CMD app:app; R-02 sin psycopg2; R-03 localhost; R-04 wrongpass; R-05 depends_on simple"],
    ["db", "postgres:16-alpine", "5432 (interno)", "POSTGRES_PASSWORD: rescue123",
     "R-08 volumen anónimo; sin healthcheck"],
], [2.0, 3.0, 3.0, 4.2, 3.8])
para("Tabla 1: Servicios del paquete recibido.", size=9).runs[0].italic = True
f = nextfig()
para(f"La Figura {f} muestra el flujo previsto y dónde se rompía. Una petición del navegador debía entrar por el "
     "puerto 8080 del host al Nginx, que sirve index.html y reenvía /api/* al backend en el puerto 8000. El backend "
     "consulta PostgreSQL en el puerto 5432. En el paquete recibido ese flujo fallaba en todos los tramos.")
figure("arquitectura_inicial.png", "Arquitectura inicial con las conexiones fallidas (rojo, punteado) y la falla de cada tramo.", 16)

# ------------------------------------------------------------------ 3. Metodología
h1("Metodología de diagnóstico")
para("Cada falla siguió la misma secuencia: síntoma → evidencia → causa raíz → corrección → verificación. "
     "No se modificó nada sin evidencia previa. Cada corrección fue un cambio mínimo, con un commit propio que "
     "incluye su ficha de bitácora y sus evidencias.")
para("Se trabajó de dentro hacia afuera: primero que el backend arrancara (R-01, R-02), luego su conexión con la "
     "base de datos (R-03, R-04) y el orden de arranque (R-05), después la exposición al host (R-06) y el proxy (R-07), "
     "y por último la persistencia (R-08). Este orden fue necesario porque las fallas estaban en cascada: al corregir "
     "una aparecía la siguiente en el mismo log.")
table(["Comando", "Qué aportó", "Incidencias"], [
    ["docker compose config", "Configuración efectiva: variables, puertos, depends_on", "R-03, R-04, R-05, M-01"],
    ["docker compose ps -a", "Estado, código de salida y puertos publicados", "R-01 a R-06, P1, P4"],
    ["docker compose logs <servicio>", "Mensaje de error exacto de cada servicio", "R-01 a R-05, R-07, M-03, P5"],
    ["docker inspect (Config.Cmd, Mounts, RestartPolicy, State.Health)", "Datos del contenedor no visibles en ps",
     "R-01, R-05, R-08, M-02, P5"],
    ["docker compose run --rm --entrypoint …", "Revisar la imagen sin arrancar la app (ls /app, pip list, DNS)",
     "R-01, R-02, R-03"],
    ["docker compose exec … (netstat, wget, grep, psql)", "Vista desde dentro del contenedor",
     "R-06, R-07, M-03, P2"],
    ["docker network inspect / docker volume ls", "Red del proyecto y volúmenes", "R-03, R-08"],
    ["curl", "Prueba desde el host", "R-06, R-07, R-08, P2 a P6"],
    ["git diff / git show", "Cambio aplicado en cada commit", "Todas"],
], [6.0, 6.5, 3.5])
para("Tabla 2: Comandos de diagnóstico utilizados.", size=9).runs[0].italic = True

# ------------------------------------------------------------------ 4. Bitácora
h1("Bitácora de reparaciones")
para("Cada subsección resume la ficha bitacora/R-0X.md. Las figuras son capturas generadas a partir de las salidas "
     "reales de evidencias/: solo se seleccionaron líneas, sin modificarlas. \"…\" indica líneas omitidas y \"↪\" la "
     "continuación de una línea larga. Los errores aparecen en rojo y los resultados correctos en verde.")

INC = [
    ("R-01", "El backend no arranca: módulo app inexistente", {
        "Incidencia": "Al levantar el stack, el contenedor backend termina de inmediato.",
        "Síntoma": "docker compose ps -a: backend en \"Exited (1) 8 seconds ago\"; db y frontend en Up.",
        "Evidencia": "Log: ERROR: Error loading ASGI app. Could not import module \"app\". Config.Cmd = "
                     "[uvicorn app:app --host 0.0.0.0 --port 8000]. En /app solo existen main.py y requirements.txt.",
        "Causa raíz": "El CMD indica a uvicorn el módulo app, que no existe; la API está definida en main.py.",
        "Cambio aplicado": "backend/Dockerfile: CMD [\"uvicorn\", \"app:app\", …] → CMD [\"uvicorn\", \"main:app\", …].",
        "Justificación": "Se apunta al módulo real sin renombrar archivos ni modificar el código de la API.",
        "Verificación": "Config.Cmd = [uvicorn main:app …]; el traceback llega a /app/main.py, línea 13 (el módulo se "
                        "importa). Aparece la falla siguiente: ModuleNotFoundError (R-02).",
        "Impacto": "La API nunca arranca y toda la aplicación queda inutilizable.",
    }, "logs, Config.Cmd y contenido de /app en la imagen", "uvicorn ya importa main.py; aparece el error de R-02"),
    ("R-02", "Falta el driver psycopg2", {
        "Incidencia": "Tras R-01, el backend vuelve a terminar con Exited (1) al importar main.py.",
        "Síntoma": "El traceback se produce en create_engine(DATABASE_URL).",
        "Evidencia": "ModuleNotFoundError: No module named 'psycopg2'. pip list solo muestra SQLAlchemy 2.0.36. "
                     "requirements.txt no incluye ningún driver.",
        "Causa raíz": "Una URL postgresql:// usa por defecto el dialecto psycopg2, pero el paquete no está declarado.",
        "Cambio aplicado": "backend/requirements.txt: se agrega psycopg2-binary==2.9.10.",
        "Justificación": "La wheel binaria incluye libpq: no requiere gcc ni libpq-dev en python:3.12-slim. Versión "
                         "fijada como las demás dependencias.",
        "Verificación": "pip list: psycopg2-binary 2.9.10. El backend ya intenta conectarse y falla con "
                        "\"connection to server at localhost … Connection refused\", Exited (3) (R-03).",
        "Impacto": "Sin driver no se puede crear el engine y la API no arranca.",
    }, "ModuleNotFoundError y pip list sin driver", "driver instalado; aparece el error de conexión de R-03"),
    ("R-03", "DATABASE_URL apunta a localhost", {
        "Incidencia": "El evento startup falla al conectar con PostgreSQL; el backend termina con Exited (3).",
        "Síntoma": "Application startup failed. Exiting.",
        "Evidencia": "connection to server at \"localhost\" (::1) y (127.0.0.1), port 5432 failed: Connection refused. "
                     "DATABASE_URL = …@localhost:5432/appdb. Desde la imagen del backend, db resuelve a 172.18.0.2 y "
                     "localhost a 127.0.0.1.",
        "Causa raíz": "Cada contenedor tiene su propio namespace de red: localhost es el propio backend, donde no hay "
                      "PostgreSQL. La base de datos se alcanza por el nombre de servicio db.",
        "Cambio aplicado": "compose.yaml (backend.environment): @localhost:5432 → @db:5432.",
        "Justificación": "El nombre de servicio es estable aunque cambie la IP. La contraseña se corrige aparte (R-04).",
        "Verificación": "El backend conecta con \"db\" (172.18.0.2):5432 y PostgreSQL responde con FATAL: password "
                        "authentication failed (R-04).",
        "Impacto": "El backend nunca alcanza la base de datos.",
    }, "conexión rechazada en localhost y resolución DNS de db", "la conexión llega a db; aparece el error de R-04"),
    ("R-04", "Contraseña distinta de POSTGRES_PASSWORD", {
        "Incidencia": "PostgreSQL rechaza la autenticación del backend.",
        "Síntoma": "Backend en Exited (3); el error aparece tanto en el backend como en db.",
        "Evidencia": "FATAL: password authentication failed for user \"appuser\" (backend y db). DETAIL: pg_hba.conf "
                     "line 128 \"host all all all scram-sha-256\". DATABASE_URL usa wrongpass; POSTGRES_PASSWORD es rescue123.",
        "Causa raíz": "El usuario se creó con rescue123, pero el backend se autentica con wrongpass.",
        "Cambio aplicado": "compose.yaml: appuser:wrongpass@ → appuser:rescue123@.",
        "Justificación": "Se ajusta el cliente al servidor: POSTGRES_PASSWORD solo se aplica al inicializar los datos.",
        "Verificación": "Backend Up; log \"Application startup complete.\"; GET /health dentro del contenedor → "
                        "{\"status\":\"ok\",\"database\":\"reachable\"}.",
        "Impacto": "La API no arranca y no se crea la tabla items.",
    }, "FATAL de autenticación en backend y db", "Application startup complete y /health reachable"),
    ("R-05", "depends_on no espera a PostgreSQL", {
        "Incidencia": "depends_on simple solo garantiza que db se haya iniciado, no que acepte conexiones.",
        "Síntoma": "Con db detenido, el backend queda en Exited (3) y no se recupera cuando db vuelve.",
        "Evidencia": "Prueba controlada: stop db + restart backend → Exited (3); RestartCount=0 Policy=no ExitCode=3; "
                     "10 s después de start db sigue Exited (3). El log de db muestra un servidor temporal [40] \"ready\" "
                     "(15:23:09.020) antes del definitivo [1] (15:23:09.601).",
        "Causa raíz": "La forma corta de depends_on equivale a service_started, db no tiene healthcheck y no hay política "
                      "de reinicio.",
        "Cambio aplicado": "compose.yaml: healthcheck pg_isready en db (interval 5s, timeout 3s, retries 10) y "
                           "depends_on: db: condition: service_healthy en backend.",
        "Justificación": "pg_isready viene en la imagen; $$ hace que las variables se expandan dentro del contenedor. "
                         "El reinicio automático se agrega en M-02.",
        "Verificación": "down y luego up --build -d: \"db-1 Waiting\" y \"db-1 Healthy\" aparecen antes de "
                        "\"backend-1 Starting\"; db (healthy); /health ok.",
        "Impacto": "Arranque intermitente según la velocidad del equipo, sin recuperación automática.",
    }, "prueba controlada: el backend queda caído (Policy=no)", "db Healthy antes de iniciar el backend"),
    ("R-06", "Puerto del frontend mal mapeado", {
        "Incidencia": "El frontend figura Up, pero no responde en http://localhost:8080/.",
        "Síntoma": "curl: (56) Recv failure: Connection reset by peer.",
        "Evidencia": "ps: 0.0.0.0:8080->8080/tcp. netstat dentro del contenedor: LISTEN en 0.0.0.0:80. wget a "
                     "127.0.0.1:80 devuelve el HTML; a 127.0.0.1:8080 da Connection refused.",
        "Causa raíz": "Se publica el puerto 8080 del contenedor, pero Nginx escucha en el 80 (listen 80; EXPOSE 80).",
        "Cambio aplicado": "compose.yaml (frontend.ports): \"8080:8080\" → \"8080:80\".",
        "Justificación": "El formato es HOST:CONTENEDOR. Se mantiene el 8080 del host y se apunta al puerto real.",
        "Verificación": "ps: 0.0.0.0:8080->80/tcp; curl / → HTTP 200 con el título de la página. /api/health → 502 (R-07).",
        "Impacto": "Nadie puede acceder a la aplicación desde fuera de Docker.",
    }, "conexión reiniciada y Nginx escuchando en :80", "HTTP 200 en el puerto 8080; /api sigue en 502 (R-07)"),
    ("R-07", "Nginx reenvía /api/ a localhost", {
        "Incidencia": "La página carga, pero la API responde 502 Bad Gateway.",
        "Síntoma": "GET /api/health → HTTP/1.1 502 Bad Gateway. Según el código de index.html, la página muestra "
                   "\"Error: Backend no saludable\" [FALTA EVIDENCIA: captura del navegador con ese mensaje].",
        "Evidencia": "Log de Nginx: connect() failed (111: Connection refused) while connecting to upstream, con upstream "
                     "\"http://127.0.0.1:8000/health\" y \"http://[::1]:8000/health\" (4 veces cada uno). proxy_pass "
                     "http://localhost:8000/ (línea 13). Desde el frontend, wget http://backend:8000/health sí responde.",
        "Causa raíz": "Dentro del contenedor de Nginx, localhost es el propio frontend; la API está en el servicio backend.",
        "Cambio aplicado": "frontend/nginx.conf: proxy_pass http://localhost:8000/; → proxy_pass http://backend:8000/;",
        "Justificación": "Solo cambia el host. La barra final se mantiene para quitar el prefijo /api/.",
        "Verificación": "/api/health → 200 OK reachable; POST /api/items → 201 (id 1); GET /api/items lo lista.",
        "Impacto": "La interfaz no puede leer ni guardar registros.",
    }, "502 y upstream hacia 127.0.0.1 / [::1]", "flujo completo: health 200, POST 201 y GET"),
    ("R-08", "Pérdida de datos en down/up", {
        "Incidencia": "Los registros desaparecen después de docker compose down + up -d.",
        "Síntoma": "GET /api/items devolvía el registro \"prueba R-07\"; después de down + up devuelve [].",
        "Evidencia": "Mounts de db: volumen anónimo f046c452… antes y bad3740c… después; docker volume ls acumula "
                     "volúmenes con nombre hash.",
        "Causa raíz": "La imagen postgres declara VOLUME /var/lib/postgresql/data. Sin montaje explícito, cada "
                      "contenedor nuevo recibe un volumen anónimo vacío.",
        "Cambio aplicado": "compose.yaml: name: aci606-rescue; en db, volumes: pgdata:/var/lib/postgresql/data; "
                           "declaración volumes: pgdata. Antes se ejecutó docker compose down.",
        "Justificación": "Un volumen nombrado sobrevive a down. name: fija el nombre del volumen "
                         "(aci606-rescue_pgdata), sin depender de la carpeta.",
        "Verificación": "Se creó \"persistente R-08\" y siguió presente después de down + up -d. Mounts: "
                        "aci606-rescue_pgdata.",
        "Impacto": "Cualquier recreación del stack borra la base de datos.",
    }, "volumen anónimo distinto en cada contenedor y lista vacía", "el registro sobrevive a down + up"),
]
FIELDS = ["Incidencia", "Síntoma", "Evidencia", "Causa raíz", "Cambio aplicado", "Justificación", "Verificación", "Impacto"]

for rid, title, data, cap_err, cap_ver in INC:
    h2(f"{rid} — {title}")
    n = rid[-1]
    h, msg = HASH[rid]
    table(["Campo", "Registro del equipo"], [[(k, True), data[k]] for k in FIELDS], [2.6, 13.4])
    f1 = nextfig()
    a = annex(f"R0{n}_diff.png", f"{rid}: cambio aplicado (git show {h}).")
    para(f"Evidencia en la Figura {f1} y verificación en la Figura {f1 + 1}; el diff del commit está en la "
         f"Figura {a} (anexos). Commit: ", space_after=2).add_run(f"{h} {msg}").bold = True
    figure(f"R0{n}_error.png", f"{rid}: {cap_err} (evidencias/{rid}_diagnostico.txt).")
    figure(f"R0{n}_verificacion.png", f"{rid}: {cap_ver} (evidencias/{rid}_verificacion.txt).")

# ------------------------------------------------------------------ 5. Mejoras
h1("Mejoras")
MEJ = [
    ("M-01", "Configuración externalizada",
     "compose.yaml usa ${POSTGRES_USER:-appuser}, ${POSTGRES_PASSWORD:-rescue123}, ${POSTGRES_DB:-appdb} y "
     "${FRONTEND_PORT:-8080}:80, y DATABASE_URL se arma con esas mismas variables. Se agregaron .env.example, .gitignore "
     "(.env, __pycache__/, *.pyc) y .dockerignore en backend y frontend. main.py ya no tiene una URL con contraseña "
     "por defecto: si falta DATABASE_URL lanza RuntimeError.",
     "Una sola fuente de credenciales evita repetir R-04. Los valores por defecto permiten que funcione un clon limpio sin .env.",
     "Sin .env, docker compose config muestra los valores por defecto. Con FRONTEND_PORT=8081 el puerto pasa a "
     "0.0.0.0:8081->80/tcp (HTTP 200) y el 8080 deja de responder. git check-ignore confirma que .env se ignora. "
     "Con DATABASE_URL vacía aparece RuntimeError: La variable de ambiente DATABASE_URL no está definida."),
    ("M-02", "Healthchecks, reinicio y red explícita",
     "Healthcheck del backend con Python (python:3.12-slim no trae curl) contra /health, y del frontend con wget. "
     "Frontend con depends_on backend service_healthy. restart: unless-stopped y red app_net en los 3 servicios. "
     "PYTHONDONTWRITEBYTECODE=1 y PYTHONUNBUFFERED=1 en el Dockerfile.",
     "Un servicio \"Up\" no es necesariamente un servicio sano. /health ejecuta SELECT 1, así que mide la API y la base de datos.",
     "El arranque muestra db Healthy → backend Healthy → frontend. ps lista los 3 servicios (healthy). Health del "
     "backend: {\"Status\":\"healthy\",\"FailingStreak\":0,…}. Los 3 con Restart=unless-stopped y red aci606-rescue_app_net."),
    ("M-03", "Nginx resistente a la recreación del backend",
     "nginx.conf pasa a ser una plantilla (/etc/nginx/templates/default.conf.template, procesada con envsubst) con "
     "resolver 127.0.0.11 valid=10s ipv6=off, set $backend_upstream http://${BACKEND_HOST}:${BACKEND_PORT}, "
     "rewrite ^/api/(.*)$ /$1 break y proxy_pass $backend_upstream.",
     "Evidencia previa: con el backend detenido, reiniciar el frontend provoca [emerg] host not found in upstream "
     "\"backend\", Restarting (1), RestartCount=6, y la página entera queda caída (Figura A3, anexos).",
     "La configuración generada muestra http://backend:8000. Con el backend detenido, / → 200 y /api/health → 502 "
     "(\"backend could not be resolved\"). Tras start backend, /api/health → 200 sin reiniciar Nginx (StartedAt sin cambios)."),
    ("M-04", "Documentación reproducible",
     "README con requisitos, tabla de variables, pasos para construir, iniciar, verificar con curl y psql, detener y "
     "recrear, más diagnóstico, estructura y advertencia sobre down -v. docs/arquitectura.md con diagramas mermaid "
     "inicial y final. .devcontainer/devcontainer.json con la imagen universal:2 y forwardPorts [8080].",
     "La solución debe poder reproducirse sin conocer su historial.",
     "Los comandos del README se ejecutaron tal como están escritos: / → 200, /api/health reachable, POST id 2 y "
     "SELECT con 2 filas. devcontainer.json es JSON válido. Los diagramas mermaid no se renderizaron localmente."),
]
for mid, title, que, porque, verif in MEJ:
    h2(f"{mid} — {title}")
    h, msg = HASH[mid]
    a_diff = annex(f"M0{mid[-1]}_diff.png", f"{mid}: fragmentos clave de git show {h} (\"…\" = líneas omitidas).")
    if mid == "M-03":
        a_prev = annex("M03_error.png", "M-03: evidencia previa, Nginx en bucle sin backend (evidencias/M-03_diagnostico.txt).")
        porque = porque.replace("Figura A3", f"Figura {a_prev}")
    a_ver = annex(f"M0{mid[-1]}_verificacion.png", f"{mid}: verificación (evidencias/{mid}_verificacion.txt).")
    para(que, bold_prefix="Qué se hizo: ")
    para(porque, bold_prefix="Por qué: ")
    para(verif + f" Salida en la Figura {a_ver} (anexos).", bold_prefix="Verificación: ")
    p = para(f"Diff en la Figura {a_diff} (anexos). Commit: ", space_after=2)
    p.add_run(f"{h} {msg}").bold = True

# ------------------------------------------------------------------ 6. Arquitectura final
h1("Arquitectura final")
f = nextfig()
para(f"La Figura {f} muestra la arquitectura reparada. Los tres servicios comparten la red app_net, solo el frontend "
     "publica un puerto en el host y la base de datos persiste en un volumen nombrado. La Tabla 3 resume la configuración.")
figure("arquitectura_final.png", "Arquitectura final: red app_net, healthchecks (hc), volumen pgdata, .env y orden de arranque.", 16)
table(["Aspecto", "Configuración final (compose.yaml)"], [
    [("Proyecto", True), "name: aci606-rescue"],
    [("Red", True), "app_net (aci606-rescue_app_net), compartida por frontend, backend y db"],
    [("Puertos", True), "host ${FRONTEND_PORT:-8080} → frontend:80. backend:8000 y db:5432 solo internos"],
    [("Enrutamiento", True), "Nginx /api/* → http://${BACKEND_HOST}:${BACKEND_PORT} (backend:8000), sin el prefijo /api; "
                             "resolver 127.0.0.11"],
    [("Variables", True), "POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB y FRONTEND_PORT con valores por defecto; "
                          "DATABASE_URL compuesta; BACKEND_HOST y BACKEND_PORT"],
    [("Persistencia", True), "volumen nombrado aci606-rescue_pgdata → /var/lib/postgresql/data"],
    [("Healthchecks", True), "db: pg_isready (5s/3s/10). backend: python urlopen /health (10s/5s/5, start 10s). "
                             "frontend: wget / (10s/3s/3)"],
    [("Dependencias", True), "backend → db: service_healthy. frontend → backend: service_healthy"],
    [("Reinicio", True), "restart: unless-stopped en los 3 servicios"],
], [3.2, 12.8])
para("Tabla 3: Resumen de la configuración final.", size=9).runs[0].italic = True

# ------------------------------------------------------------------ 7. Pruebas
h1("Pruebas de validación")
para("Las pruebas se ejecutaron sobre la versión final (commit 768d438). La Tabla 4 resume los resultados, y cada "
     "subsección describe el procedimiento con su evidencia.")
PR = [
    ("P1", "Arranque limpio", "docker compose down y luego docker compose up --build -d; ps después de 25 s.",
     "db Healthy → backend Healthy → frontend. Los 3 servicios en Up (healthy).", "P1_arranque_limpio.txt"),
    ("P2", "Comunicación", "GET /api/health, POST /api/items y SELECT * FROM items con psql en db.",
     "200 con {\"status\":\"ok\",\"database\":\"reachable\"}; POST 201 (id 3); psql muestra 3 filas.", "P2_comunicacion.txt"),
    ("P3", "Persistencia", "down + up -d, y luego up -d --force-recreate db (id 751d093220c3 → 3fa19aaeded0).",
     "Los 3 registros permanecen en ambos casos.", "P3_persistencia.txt"),
    ("P4", "Fallo controlado", "docker compose stop db y espera de 60 s.",
     "Frontend / → 200; /api/health → 503 (could not translate host name \"db\"); backend (unhealthy).",
     "P4_fallo_controlado.txt"),
    ("P5", "Diagnóstico", "Logs del backend e inspect de .State.Health.",
     "Logs con GET /health 503; Status unhealthy, FailingStreak 6, HTTP Error 503.", "P5_diagnostico.txt"),
    ("P6", "Recuperación", "docker compose start db y espera de 35 s.",
     "Los 3 servicios healthy; /api/health 200; datos intactos. El backend no se reinició: RestartCount=0 y mismo StartedAt.",
     "P6_recuperacion.txt"),
]
table(["Prueba", "Resultado", "Estado"], [[f"{p[0]} {p[1]}", p[3], "OK"] for p in PR], [3.0, 11.5, 1.5])
para("Tabla 4: Resultado de las pruebas P1 a P6.", size=9).runs[0].italic = True
for pid, title, proc, res, ev in PR:
    a = annex(f"{pid}.png", f"{pid}: {title.lower()} (evidencias/{ev}).")
    extra = ""
    if pid == "P2":
        extra = f" La Figura {nextfig()} muestra la aplicación en el navegador."
    para(f"{proc} Resultado: {res} Evidencia: Figura {a} (anexos).{extra}", bold_prefix=f"{pid} {title}. ")
    if pid == "P2":
        figure(ROOT / "capturas" / "navegador_app.png",
               "Captura del navegador del equipo (capturas/navegador_app.png): \"Backend: ok | DB: reachable\" y "
               "registros #1 a #4, tomada después de las pruebas.")

# ------------------------------------------------------------------ 8. Conclusiones
h1("Conclusiones")
para("Aprendizajes técnicos:", bold_prefix=None).runs[0].bold = True
bullet("dentro de un contenedor, localhost es el propio contenedor. Entre servicios se usa el nombre del servicio "
       "(R-03 y R-07 fueron el mismo error, en dos capas distintas).", "localhost entre contenedores: ")
bullet("un contenedor Up puede no atender (R-06, R-07). Los healthchecks convierten \"está corriendo\" en \"funciona\".",
       "running vs healthy: ")
bullet("cada corrección destapó la falla siguiente en el mismo log (R-01 → R-02 → R-03 → R-04). Por eso se corrigió "
       "una falla por commit, siempre con evidencia.", "Fallas en cascada: ")
bullet("service_started no garantiza que PostgreSQL acepte conexiones. service_healthy con pg_isready sí.",
       "depends_on vs service_healthy: ")
bullet("sin un volumen nombrado, los datos dependen del ciclo de vida del contenedor.", "Persistencia: ")
para("Decisiones adoptadas: cambios mínimos sobre los archivos recibidos, nombres de servicio en vez de IP, "
     "configuración por variables con valores por defecto, healthchecks en los tres servicios, resolución DNS "
     "dinámica en Nginx y un proyecto con nombre fijo para estabilizar el nombre del volumen.")
para("Limitaciones:", bold_prefix=None).runs[0].bold = True
bullet("la contraseña por defecto (rescue123) es visible en .env.example y en compose.yaml. Sirve para la evaluación, "
       "no para producción.")
bullet("GET /items no captura excepciones en main.py, así que con la base de datos caída respondería 500 en vez de 503. "
       "Deducido del código; no se ejecutó esa prueba [FALTA EVIDENCIA: salida de GET /api/items con db detenida].")
bullet("cambiar POSTGRES_PASSWORD no tiene efecto sobre un volumen pgdata ya inicializado (comportamiento documentado "
       "de la imagen postgres; no se probó). Requiere ALTER USER.")
bullet("no hay backups del volumen, TLS ni réplicas.")
bullet("main.py usa APIs obsoletas: @app.on_event(\"startup\") (línea 20) y datetime.utcnow() (línea 65). No se "
       "modificaron porque funcionan y no formaban parte de las fallas.")

# ------------------------------------------------------------------ 9. Repositorio
h1("Repositorio")
para(REPO, bold_prefix="Enlace: ")
para("La Tabla 5 muestra el historial de commits obtenido con git log --oneline --reverse.")


def rel(msg):
    for tag in ["R-0%d" % i for i in range(1, 9)] + ["M-0%d" % i for i in range(1, 5)]:
        if f"({tag})" in msg:
            return tag
    if msg.startswith("test"):
        return "P1–P6"
    if msg.startswith("chore"):
        return "Paso 0"
    if "copia de referencia" in msg:
        return "Paso 0"
    if "índice" in msg:
        return "Cierre"
    return "Entrega del profesor"


table(["Hash", "Mensaje", "Relacionado"], [[h, m, rel(m)] for h, m in COMMITS], [1.8, 11.7, 2.5], size=8.5)
para("Tabla 5: Historial de commits.", size=9).runs[0].italic = True

# ------------------------------------------------------------------ 10. Anexos
doc.add_page_break()
h1("Anexos")
h2("compose.yaml final")
code_block((ROOT / "compose.yaml").read_text())
h2("frontend/nginx.conf final")
code_block((ROOT / "frontend" / "nginx.conf").read_text())
h2("Figuras complementarias")
para("Diffs de cada commit, verificaciones de las mejoras y capturas de las pruebas P1 a P6. Mismas convenciones "
     "que en el cuerpo: \"…\" indica líneas omitidas y \"↪\" la continuación de una línea larga.")
AN_OLD = [("M01_verificacion.png", "M-01: verificación (evidencias/M-01_verificacion.txt)."),
      ("M02_verificacion.png", "M-02: verificación (evidencias/M-02_verificacion.txt)."),
      ("M03_error.png", "M-03: evidencia previa, Nginx en bucle sin backend (evidencias/M-03_diagnostico.txt)."),
      ("M03_verificacion.png", "M-03: verificación (evidencias/M-03_verificacion.txt)."),
      ("M04_verificacion.png", "M-04: verificación de los comandos del README (evidencias/M-04_verificacion.txt).")]
for i, (img, c) in enumerate(ANNEX, 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(IMG / img), width=Cm(14))
    label = f"A{i}"
    cp = doc.add_paragraph(f"Figura {label}: {c}", style="Caption")
    cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
h2("Archivos de evidencias/")
files = sorted(p.name for p in (ROOT / "evidencias").glob("*.txt"))
code_block("\n".join(files), size=8)
para("Nota: 00_config_desde_raiz_sin_mover.txt y 00_ps_desde_raiz_sin_mover.txt están vacíos. Corresponden a un "
     "intento previo desde la raíz, sin redirigir stderr; el error quedó en 00_config_desde_raiz_verificacion.txt.", size=9)

doc.save(OUT)
print("OK", OUT, "figuras cuerpo:", FIG[0])
