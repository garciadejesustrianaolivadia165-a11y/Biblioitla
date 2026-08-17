"""
Graba un video de demostracion del primer Release recorriendo la aplicacion
con un navegador real (Playwright).

Genera evidencias/demo/demo_biblioitla.webm y, si hay ffmpeg, tambien .mp4.
El video NO lleva audio: sirve como captura de pantalla del incremento, lista
para narrar encima si se desea.

Uso:  python3 herramientas/grabar_demo.py
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "evidencias" / "demo"
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FFMPEG = "/opt/pw-browsers/ffmpeg-1011/ffmpeg-linux"

PAUSA_CORTA = 700
PAUSA_LARGA = 1600


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def arrancar_servidor():
    bd = tempfile.NamedTemporaryFile(suffix="_demo.db", delete=False)
    bd.close()
    puerto = puerto_libre()
    entorno = os.environ | {
        "BIBLIOITLA_DB": f"sqlite:///{bd.name}",
        "BIBLIOITLA_SECRETO": "secreto-demo",
        "PYTHONPATH": str(RAIZ),
    }
    proceso = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.principal:aplicacion",
         "--host", "127.0.0.1", "--port", str(puerto), "--log-level", "warning"],
        cwd=str(RAIZ), env=entorno,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    url = f"http://127.0.0.1:{puerto}"
    for _ in range(60):
        try:
            if urllib.request.urlopen(f"{url}/api/salud", timeout=1).status == 200:
                return proceso, url, bd.name
        except Exception:
            time.sleep(0.5)
    proceso.kill()
    raise RuntimeError("El servidor no arranco")


def recorrido(pagina, url):
    """Guion del video, en el orden en que se presenta el Release 1."""

    def paso(texto, espera=PAUSA_CORTA):
        print(f"  · {texto}")
        pagina.wait_for_timeout(espera)

    # 1. Acceso
    pagina.goto(f"{url}/login")
    paso("Pantalla de acceso", PAUSA_LARGA)
    pagina.fill('[data-test="usuario"]', "admin")
    paso("Usuario")
    pagina.fill('[data-test="clave"]', "BiblioITLA2026")
    paso("Contrasena")
    pagina.click('[data-test="entrar"]')
    pagina.wait_for_url(f"{url}/")
    paso("Panel de control con los indicadores", PAUSA_LARGA)

    # 2. Catalogo
    pagina.click("text=Libros")
    pagina.wait_for_url("**/libros")
    paso("Catalogo completo", PAUSA_LARGA)

    pagina.fill('[data-test="isbn"]', "978-0596517748")
    pagina.fill('[data-test="titulo"]', "JavaScript: The Good Parts")
    pagina.fill('[data-test="autor"]', "Douglas Crockford")
    pagina.fill('[data-test="categoria"]', "Programacion")
    pagina.fill('[data-test="ejemplares"]', "2")
    paso("Formulario de alta relleno", PAUSA_LARGA)
    pagina.click('[data-test="guardar-libro"]')
    pagina.wait_for_url("**/libros?*")
    paso("Libro registrado (HU-02)", PAUSA_LARGA)

    # 3. Busqueda
    pagina.fill('[data-test="buscar"]', "Bosch")
    pagina.click('[data-test="btn-buscar"]')
    pagina.wait_for_url("**/libros?q=*")
    paso("Busqueda por autor (HU-03)", PAUSA_LARGA)

    # 4. Socios
    pagina.goto(f"{url}/socios")
    paso("Listado de socios", PAUSA_CORTA)
    pagina.fill('[data-test="matricula"]', "20240777")
    pagina.fill('[data-test="nombre-socio"]', "Carlos Alberto Nunez")
    pagina.fill('[data-test="correo"]', "20240777@itla.edu.do")
    pagina.click('[data-test="guardar-socio"]')
    pagina.wait_for_url("**/socios?*")
    paso("Socio registrado (HU-09)", PAUSA_LARGA)

    # 5. Prestamo
    pagina.goto(f"{url}/prestamos")
    paso("Pantalla de prestamos", PAUSA_CORTA)
    pagina.select_option('[data-test="sel-socio"]', index=1)
    pagina.select_option('[data-test="sel-libro"]', index=1)
    paso("Socio y libro seleccionados", PAUSA_LARGA)
    pagina.click('[data-test="guardar-prestamo"]')
    pagina.wait_for_url("**/prestamos?*")
    paso("Prestamo registrado (HU-04)", PAUSA_LARGA)

    # 6. Regla de negocio: no se puede repetir el prestamo
    pagina.select_option('[data-test="sel-socio"]', index=1)
    pagina.select_option('[data-test="sel-libro"]', index=1)
    pagina.click('[data-test="guardar-prestamo"]')
    pagina.wait_for_url("**/prestamos?*")
    paso("La regla de negocio bloquea el prestamo duplicado", PAUSA_LARGA + 600)

    # 7. El panel refleja el cambio
    pagina.goto(f"{url}/")
    paso("El panel muestra el prestamo activo (HU-08)", PAUSA_LARGA)

    # 8. Devolucion
    pagina.goto(f"{url}/prestamos")
    pagina.click('[data-test="devolver"]')
    pagina.wait_for_url("**/prestamos?*")
    paso("Devolucion registrada (HU-05)", PAUSA_LARGA)
    pagina.goto(f"{url}/prestamos?estado=devueltos")
    paso("Historial de devoluciones (HU-07)", PAUSA_LARGA)

    pagina.goto(f"{url}/")
    paso("Panel final", PAUSA_LARGA)


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    for viejo in DESTINO.glob("*.webm"):
        viejo.unlink()

    proceso, url, bd = arrancar_servidor()
    print(f"Servidor de demostracion en {url}")
    try:
        with sync_playwright() as p:
            opciones = {"args": ["--no-sandbox"]}
            if Path(CHROMIUM).exists():
                opciones["executable_path"] = CHROMIUM
            navegador = p.chromium.launch(**opciones)
            contexto = navegador.new_context(
                viewport={"width": 1440, "height": 900},
                record_video_dir=str(DESTINO),
                record_video_size={"width": 1440, "height": 900},
                locale="es-DO")
            pagina = contexto.new_page()
            pagina.set_default_timeout(15_000)
            recorrido(pagina, url)
            contexto.close()          # al cerrar se guarda el video
            navegador.close()
    finally:
        proceso.terminate()
        Path(bd).unlink(missing_ok=True)

    videos = sorted(DESTINO.glob("*.webm"))
    if not videos:
        raise SystemExit("No se genero ningun video")
    final = DESTINO / "demo_biblioitla.webm"
    if videos[0] != final:
        shutil.move(str(videos[0]), final)
    print(f"Video: {final} ({final.stat().st_size / 1e6:.1f} MB)")

    # El ffmpeg que trae Playwright solo sabe escribir webm; si esta
    # instalado imageio-ffmpeg se usa su binario completo para el mp4.
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg = FFMPEG if Path(FFMPEG).exists() else None
    if ffmpeg:
        mp4 = DESTINO / "demo_biblioitla.mp4"
        r = subprocess.run([ffmpeg, "-y", "-i", str(final), "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-crf", "23",
                            "-movflags", "+faststart", str(mp4)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if r.returncode == 0 and mp4.exists():
            print(f"Video MP4: {mp4} ({mp4.stat().st_size / 1e6:.1f} MB)")
        else:
            print("(no se pudo convertir a mp4; queda el .webm)")
    else:
        print("(ffmpeg no disponible; queda el .webm)")


if __name__ == "__main__":
    main()
