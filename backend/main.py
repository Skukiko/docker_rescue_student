import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("La variable de ambiente DATABASE_URL no está definida")

logger = logging.getLogger("uvicorn.error")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


def create_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY,
                name VARCHAR(80) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_schema()
    yield
    engine.dispose()


app = FastAPI(title="ACI606 Docker Rescue API", version="1.0", lifespan=lifespan)


@app.exception_handler(OperationalError)
async def database_unavailable(_: Request, exc: OperationalError) -> JSONResponse:
    # Si PostgreSQL no responde, cualquier endpoint devuelve 503 (no 500).
    logger.warning("Base de datos no disponible: %s", exc.orig)
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception as exc:
        # El detalle va al log del contenedor, no a la respuesta pública.
        logger.warning("Healthcheck: base de datos no disponible: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable")


@app.get("/items")
def list_items():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, name, created_at FROM items ORDER BY id")
        ).mappings().all()
    return [dict(row) for row in rows]


@app.post("/items", status_code=201)
def create_item(item: ItemIn):
    with engine.begin() as conn:
        row = conn.execute(
            text("INSERT INTO items(name) VALUES (:name) RETURNING id, name, created_at"),
            {"name": item.name},
        ).mappings().one()
    return dict(row)


@app.get("/")
def root():
    return {
        "service": "ACI606 Docker Rescue API",
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
