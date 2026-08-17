"""
Punto de entrada de BiblioITLA.

    uvicorn app.principal:aplicacion --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .base_datos import inicializar
from .routers import api, web


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    inicializar()          # crea las tablas y siembra el catalogo si hace falta
    yield


aplicacion = FastAPI(
    title="BiblioITLA",
    description="Sistema de gestion de biblioteca - Proyecto Final Programacion III",
    version="1.0.0",
    lifespan=ciclo_vida,
)

ESTATICOS = Path(__file__).parent / "static"
aplicacion.mount("/static", StaticFiles(directory=str(ESTATICOS)), name="static")

aplicacion.include_router(api.router)
aplicacion.include_router(web.router)
