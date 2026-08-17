"""
Configuracion compartida de las pruebas.

Cada prueba recibe una base de datos SQLite NUEVA y aislada. En lugar de
recargar modulos, se sustituye la dependencia `obtener_sesion` de FastAPI
(dependency_overrides), que es la forma prevista por el framework y no deja
estado global a medias entre pruebas.
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("BIBLIOITLA_SECRETO", "secreto-de-pruebas")
# La app crea su motor al importarse; se apunta a un archivo desechable para
# que arrancar el TestClient no toque la base de datos de desarrollo.
_BD_ARRANQUE = tempfile.NamedTemporaryFile(suffix="_arranque.db", delete=False)
_BD_ARRANQUE.close()
os.environ["BIBLIOITLA_DB"] = f"sqlite:///{_BD_ARRANQUE.name}"

from app.base_datos import obtener_sesion, sembrar_datos  # noqa: E402
from app.modelos import Base                              # noqa: E402
from app.principal import aplicacion                      # noqa: E402


@pytest.fixture()
def fabrica_sesiones():
    """Motor y fabrica de sesiones sobre una base de datos temporal vacia."""
    fichero = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    fichero.close()
    motor = create_engine(f"sqlite:///{fichero.name}",
                          connect_args={"check_same_thread": False})
    Base.metadata.create_all(motor)
    Fabrica = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)

    with Fabrica() as s:
        sembrar_datos(s, con_prestamos=False)

    yield Fabrica

    motor.dispose()
    Path(fichero.name).unlink(missing_ok=True)


@pytest.fixture()
def sesion(fabrica_sesiones):
    """Sesion directa contra la base temporal (pruebas de servicios)."""
    with fabrica_sesiones() as s:
        yield s


@pytest.fixture()
def cliente(fabrica_sesiones):
    """Cliente HTTP de FastAPI conectado a la base temporal."""

    def sesion_de_prueba():
        s = fabrica_sesiones()
        try:
            yield s
        finally:
            s.close()

    aplicacion.dependency_overrides[obtener_sesion] = sesion_de_prueba
    # El TestClient no dispara el lifespan si no se usa como contexto; aqui no
    # hace falta porque las tablas ya existen y los datos ya estan sembrados.
    with TestClient(aplicacion) as c:
        yield c
    aplicacion.dependency_overrides.clear()


@pytest.fixture()
def cliente_autenticado(cliente):
    """Cliente con la sesion web ya iniciada (cookie de acceso puesta)."""
    respuesta = cliente.post("/login",
                             data={"nombre_usuario": "admin",
                                   "clave": "BiblioITLA2026"},
                             follow_redirects=False)
    assert respuesta.status_code == 303, "El login de prueba deberia redirigir"
    return cliente
