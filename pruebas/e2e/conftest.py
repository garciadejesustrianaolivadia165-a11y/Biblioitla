"""
Infraestructura de las pruebas de extremo a extremo.

Levanta el servidor real (uvicorn) contra una base de datos temporal y abre
un navegador Chromium con Playwright. Se graba video y se guardan capturas
en `evidencias/`, que es la evidencia de automatizacion que pide la practica.
"""

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
EVIDENCIAS = RAIZ / "evidencias"
VIDEOS = EVIDENCIAS / "videos"

# Playwright de este entorno trae una compilacion distinta a la instalada;
# se apunta al binario disponible cuando existe.
CHROMIUM = os.environ.get("CHROMIUM_BIN", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def servidor(request):
    """Arranca uvicorn con una base de datos limpia y lo apaga al terminar."""
    fichero = tempfile.NamedTemporaryFile(suffix="_e2e.db", delete=False)
    fichero.close()
    request.session._bd_e2e = fichero.name      # la usa `datos_limpios`
    puerto = _puerto_libre()

    entorno = os.environ | {
        "BIBLIOITLA_DB": f"sqlite:///{fichero.name}",
        "BIBLIOITLA_SECRETO": "secreto-e2e",
        "PYTHONPATH": str(RAIZ),
    }
    proceso = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.principal:aplicacion",
         "--host", "127.0.0.1", "--port", str(puerto), "--log-level", "warning"],
        cwd=str(RAIZ), env=entorno,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    url = f"http://127.0.0.1:{puerto}"
    for _ in range(60):
        try:
            import urllib.request
            if urllib.request.urlopen(f"{url}/api/salud", timeout=1).status == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proceso.kill()
        salida = proceso.stdout.read().decode(errors="replace") if proceso.stdout else ""
        raise RuntimeError(f"El servidor no arranco.\n{salida}")

    yield url

    proceso.terminate()
    try:
        proceso.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proceso.kill()
    Path(fichero.name).unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def datos_limpios(servidor, request):
    """
    Devuelve la base de datos a su estado inicial antes de CADA prueba.

    El servidor vive toda la sesion (arrancarlo por prueba seria lento), asi
    que sin esto una prueba heredaria los prestamos y libros creados por la
    anterior y los resultados dependerian del orden de ejecucion.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.base_datos import sembrar_datos
    from app.modelos import Base

    motor = create_engine(f"sqlite:///{request.session._bd_e2e}")
    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)
    with sessionmaker(bind=motor)() as s:
        sembrar_datos(s, con_prestamos=False)
    motor.dispose()
    yield


@pytest.fixture(scope="session")
def navegador():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as p:
        opciones = {"args": ["--no-sandbox"]}
        if Path(CHROMIUM).exists():
            opciones["executable_path"] = CHROMIUM
        nav = p.chromium.launch(**opciones)
        yield nav
        nav.close()


@pytest.fixture()
def pagina(navegador, servidor, request):
    """Pestania nueva por prueba, con video y captura final."""
    VIDEOS.mkdir(parents=True, exist_ok=True)
    contexto = navegador.new_context(
        viewport={"width": 1400, "height": 900},
        record_video_dir=str(VIDEOS),
        record_video_size={"width": 1400, "height": 900},
        locale="es-DO")
    pag = contexto.new_page()
    pag.set_default_timeout(10_000)
    pag.base_url = servidor

    yield pag

    captura = EVIDENCIAS / "capturas" / f"{request.node.name}.png"
    captura.parent.mkdir(parents=True, exist_ok=True)
    try:
        pag.screenshot(path=str(captura), full_page=True)
    except Exception:
        pass
    contexto.close()


@pytest.fixture()
def sesion_iniciada(pagina):
    """Deja la sesion abierta en el panel principal."""
    pagina.goto(f"{pagina.base_url}/login")
    pagina.fill('[data-test="usuario"]', "admin")
    pagina.fill('[data-test="clave"]', "BiblioITLA2026")
    pagina.click('[data-test="entrar"]')
    pagina.wait_for_url(f"{pagina.base_url}/")
    return pagina
