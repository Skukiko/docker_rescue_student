#!/usr/bin/env python3
"""Genera las figuras del informe a partir de evidencias/*.txt y de git show.

- Capturas de terminal: solo líneas reales de evidencias/, sin modificar.
  Si se omiten líneas se inserta "…". Las líneas largas se parten visualmente
  (el texto no cambia; la continuación se marca con "↪").
- Diffs: salida real de `git show <hash> -- <archivos>`.
- Diagramas: graphviz.
Uso: python3 informe/generar_imagenes.py   (desde la raíz del repositorio)
"""
import re
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "evidencias"
OUT = ROOT / "informe" / "img"
OUT.mkdir(parents=True, exist_ok=True)

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FS = 26                     # px (se reduce al insertar en el docx)
COLS = 100                  # ancho máximo en caracteres antes de partir la línea
FONT = ImageFont.truetype(MONO, FS)
FONT_B = ImageFont.truetype(MONO_B, FS)
CW = FONT.getbbox("M")[2]
LH = int(FS * 1.22)
PAD = 16

BG = (30, 32, 36)
BAR = (58, 61, 68)
FG = (215, 218, 222)
CMD = (120, 190, 255)
RED = (255, 105, 97)
GREEN = (120, 220, 120)
GRAY = (140, 144, 150)
DIFF_HDR = (230, 200, 110)
HUNK = (110, 200, 220)

RE_RED = re.compile(r"Error|ERROR|Exited|FATAL|refused|\b502\b|\b503\b|ModuleNotFoundError|unhealthy|"
                    r"emerg|reset by peer|Restarting \(\d\)|Failed to connect|could not be resolved|HTTP 000")
RE_GREEN = re.compile(r"healthy|Healthy|startup complete|\"status\":\"ok\"|\b200\b|\b201\b")


def color_terminal(line: str):
    if line.startswith("$ "):
        return CMD
    if line == "…":
        return GRAY
    if RE_RED.search(line):
        return RED
    if RE_GREEN.search(line):
        return GREEN
    return FG


def color_diff(line: str):
    if line.startswith(("diff --git", "index ", "--- ", "+++ ", "new file mode")):
        return DIFF_HDR
    if line.startswith("@@"):
        return HUNK
    if line.startswith("+"):
        return GREEN
    if line.startswith("-"):
        return RED
    if line == "…":
        return GRAY
    return FG


def wrap(line: str):
    line = line.rstrip().replace("\t", "    ")
    if len(line) <= COLS:
        return [line]
    parts = textwrap.wrap(line, COLS, drop_whitespace=False, break_long_words=True,
                          replace_whitespace=False)
    return [parts[0]] + ["↪ " + p for p in parts[1:]]


def render(name: str, bar_cmd: str, lines, colorer):
    rows = []                                   # (texto, color)
    for ln in lines:
        c = colorer(ln)
        for i, part in enumerate(wrap(ln)):
            rows.append((part, c))
    bar_lines = wrap("$ " + bar_cmd)
    width = PAD * 2 + CW * (COLS + 2)          # ancho fijo: misma escala de letra en todas
    bar_h = LH * len(bar_lines) + 14
    height = bar_h + PAD * 2 + LH * len(rows)
    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width, bar_h], fill=BAR)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([PAD + i * 30, 11, PAD + i * 30 + 18, 29], fill=col)
    for i, b in enumerate(bar_lines):
        d.text((PAD + 100, 7 + i * LH), b, font=FONT_B, fill=(235, 235, 235))
    y = bar_h + PAD
    for text, col in rows:
        d.text((PAD, y), text, font=FONT, fill=col)
        y += LH
    img.save(OUT / name)
    return len(rows)


def ev_lines(fname: str, ranges):
    """Toma rangos (1-indexados, inclusivos) de un archivo de evidencia; inserta '…' entre huecos."""
    src = (EV / fname).read_text(encoding="utf-8").splitlines()
    out, last = [], None
    for a, b in ranges:
        if last is not None and a != last + 1:
            out.append("…")
        if last is None and a != 1:
            out.append("…")
        out.extend(src[a - 1:b])
        last = b
    if last is not None and last < len(src) and any(s.strip() for s in src[last:]):
        out.append("…")
    return out


def terminal(name, bar, parts):
    lines = []
    for fname, ranges in parts:
        if lines:
            lines.append("…")
        lines.extend(ev_lines(fname, ranges))
    # evita "…" duplicados consecutivos
    clean = []
    for ln in lines:
        if ln == "…" and clean and clean[-1] == "…":
            continue
        clean.append(ln)
    n = render(name, bar, clean, color_terminal)
    print(f"{name}: {n} filas")


def diff(name, commit, paths, keep=None):
    cmd = ["git", "show", "--format=", commit, "--"] + paths
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    lines = out
    if keep:
        sel, last = [], None
        for a, b in keep:
            if last is not None and a != last + 1:
                sel.append("…")
            sel.extend(out[a - 1:b])
            last = b
        if last < len(out):
            sel.append("…")
        lines = sel
    n = render(name, "git show " + commit + " -- " + " ".join(paths), lines, color_diff)
    print(f"{name}: {n} filas (diff de {len(out)} líneas)")


# ---------------------------------------------------------------- terminal
T = [
    ("R01_error.png", "docker compose logs backend", [("R-01_diagnostico.txt", [(1, 2), (4, 5), (7, 7), (11, 15)])]),
    ("R01_verificacion.png", "docker compose up --build -d backend",
     [("R-01_verificacion.txt", [(10, 12), (26, 27)])]),
    ("R02_error.png", "docker compose logs backend | tail -3", [("R-02_diagnostico.txt", [(1, 4), (6, 7), (9, 12)])]),
    ("R02_verificacion.png", "docker compose up --build -d backend",
     [("R-02_verificacion.txt", [(6, 8), (12, 13), (18, 18)])]),
    ("R03_error.png", "docker compose logs backend | grep -A1 \"connection to server\"",
     [("R-03_diagnostico.txt", [(1, 2), (4, 4), (7, 8), (10, 12)])]),
    ("R03_verificacion.png", "docker compose up -d backend",
     [("R-03_verificacion.txt", [(5, 6), (10, 10), (14, 14), (18, 18)])]),
    ("R04_error.png", "docker compose logs backend | grep FATAL", [("R-04_diagnostico.txt", [(1, 2), (5, 7), (9, 11)])]),
    ("R04_verificacion.png", "docker compose up -d backend", [("R-04_verificacion.txt", [(10, 16)])]),
    ("R05_error.png", "docker compose stop db && docker compose restart backend",
     [("R-05_diagnostico.txt", [(1, 1), (4, 4), (7, 7), (9, 9), (12, 13), (17, 18), (21, 21), (23, 23)])]),
    ("R05_verificacion.png", "docker compose down && docker compose up --build -d",
     [("R-05_verificacion.txt", [(16, 16), (32, 38), (49, 49), (51, 52)])]),
    ("R06_error.png", "curl -sS -v http://localhost:8080/",
     [("R-06_diagnostico.txt", [(1, 1), (3, 3), (5, 5), (11, 11), (13, 13), (16, 17), (27, 28)])]),
    ("R06_verificacion.png", "docker compose up -d frontend", [("R-06_verificacion.txt", [(4, 8), (11, 12)])]),
    ("R07_error.png", "curl -sS -i http://localhost:8080/api/health",
     [("R-07_diagnostico.txt", [(1, 2), (4, 5), (8, 9), (11, 12)])]),
    ("R07_verificacion.png", "docker compose up --build -d frontend", [("R-07_verificacion.txt", [(6, 8), (10, 14)])]),
    ("R08_error.png", "docker compose down && docker compose up -d",
     [("R-08_diagnostico.txt", [(1, 4), (10, 10), (15, 15), (20, 23)])]),
    ("R08_verificacion.png", "docker compose down && docker compose up -d",
     [("R-08_verificacion.txt", [(19, 20), (23, 23), (28, 28), (33, 36)])]),
    # Mejoras (verificaciones: anexos)
    ("M01_verificacion.png", "docker compose config | grep -E \"DATABASE_URL|POSTGRES_|published\"",
     [("M-01_verificacion.txt", [(1, 10), (19, 30), (40, 47)])]),
    ("M02_verificacion.png", "docker compose up --build -d",
     [("M-02_verificacion.txt", [(5, 5), (10, 16), (25, 26), (31, 33), (38, 42)])]),
    ("M03_error.png", "docker compose stop backend && docker compose restart frontend",
     [("M-03_diagnostico.txt", [(1, 1), (4, 4), (7, 20)])]),
    ("M03_verificacion.png", "docker compose exec frontend grep -n -E \"resolver|backend_upstream|rewrite\" /etc/nginx/conf.d/default.conf",
     [("M-03_verificacion.txt", [(14, 18), (26, 30), (36, 41), (43, 49)])]),
    ("M04_verificacion.png", "docker compose exec db psql -U appuser -d appdb -c \"SELECT * FROM items;\"",
     [("M-04_verificacion.txt", [(1, 4), (15, 30)])]),
    # Pruebas
    ("P1.png", "docker compose up --build -d", [("P1_arranque_limpio.txt", [(6, 6), (23, 24), (27, 28), (30, 30), (32, 36)])]),
    ("P2.png", "curl -sS -i http://localhost:8080/api/health", [("P2_comunicacion.txt", [(1, 3), (5, 7), (10, 16)])]),
    ("P3.png", "docker compose down && docker compose up -d",
     [("P3_persistencia.txt", [(1, 4), (9, 11), (17, 18), (20, 22), (26, 27), (30, 33)])]),
    ("P4.png", "docker compose stop db", [("P4_fallo_controlado.txt", [(1, 9), (11, 12)])]),
    ("P5.png", "docker inspect --format '{{json .State.Health}}' aci606-rescue-backend-1",
     [("P5_diagnostico.txt", [(1, 4), (9, 9), (11, 14)])]),
    ("P6.png", "docker compose start db", [("P6_recuperacion.txt", [(1, 3), (10, 15), (18, 18), (24, 24)])]),
]

# ---------------------------------------------------------------- diffs
D = [
    ("R01_diff.png", "748f5c2", ["backend/Dockerfile"], None),
    ("R02_diff.png", "ba9a7ac", ["backend/requirements.txt"], None),
    ("R03_diff.png", "bcfbc91", ["compose.yaml"], None),
    ("R04_diff.png", "5aa17c9", ["compose.yaml"], None),
    ("R05_diff.png", "25a69c5", ["compose.yaml"], None),
    ("R06_diff.png", "e6f1716", ["compose.yaml"], None),
    ("R07_diff.png", "89ebb3a", ["frontend/nginx.conf"], None),
    ("R08_diff.png", "8f3588f", ["compose.yaml"], None),
    # En las mejoras se muestran solo los fragmentos clave (el diff completo está en el commit).
    ("M01_diff.png", "8fb287f", ["compose.yaml", "backend/main.py"],
     [(1, 1), (9, 15), (19, 19), (27, 28), (35, 36), (44, 49)]),
    ("M02_diff.png", "af9fff7", ["compose.yaml", "backend/Dockerfile"],
     [(1, 1), (8, 9), (13, 13), (21, 25), (29, 31), (39, 40), (45, 47), (59, 60)]),
    ("M03_diff.png", "bd818be", ["frontend/nginx.conf", "frontend/Dockerfile", "compose.yaml"],
     [(1, 1), (9, 11), (15, 15), (22, 25), (29, 29), (37, 45)]),
    ("M04_diff.png", "4b36d62", [".devcontainer/devcontainer.json"], None),
]

if __name__ == "__main__":
    for name, bar, parts in T:
        terminal(name, bar, parts)
    for name, commit, paths, keep in D:
        diff(name, commit, paths, keep)
    # diagramas
    for dot in ("arquitectura_inicial", "arquitectura_final"):
        subprocess.run(["dot", "-Tpng", "-Gdpi=200", str(ROOT / "informe" / f"{dot}.dot"),
                        "-o", str(OUT / f"{dot}.png")], check=True)
        print(f"{dot}.png")
