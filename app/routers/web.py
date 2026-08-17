"""Interfaz web (HTML renderizado en el servidor con Jinja2)."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy.orm import Session

from .. import servicios
from ..base_datos import obtener_sesion
from ..reglas import MAX_PRESTAMOS_ACTIVOS, MORA_POR_DIA, ReglaNegocioError

router = APIRouter()
PLANTILLAS = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

CLAVE_COOKIE = os.environ.get("BIBLIOITLA_SECRETO", "clave-de-desarrollo-biblioitla")
firmante = URLSafeSerializer(CLAVE_COOKIE, salt="sesion")
COOKIE = "biblioitla_sesion"


def usuario_actual(request: Request) -> dict | None:
    bruto = request.cookies.get(COOKIE)
    if not bruto:
        return None
    try:
        return firmante.loads(bruto)
    except BadSignature:
        return None


def _render(request: Request, plantilla: str, **contexto):
    contexto.setdefault("usuario", usuario_actual(request))
    contexto.setdefault("max_prestamos", MAX_PRESTAMOS_ACTIVOS)
    contexto.setdefault("mora_dia", MORA_POR_DIA)
    return PLANTILLAS.TemplateResponse(request, plantilla, contexto)


def _exigir_sesion(request: Request):
    return usuario_actual(request) is not None


# ---------------------------------------------------------------- sesion ---
@router.get("/login", response_class=HTMLResponse)
def formulario_login(request: Request):
    return _render(request, "login.html")


@router.post("/login")
def procesar_login(request: Request, nombre_usuario: str = Form(...),
                   clave: str = Form(...),
                   sesion: Session = Depends(obtener_sesion)):
    usuario = servicios.autenticar(sesion, nombre_usuario, clave)
    if usuario is None:
        return _render(request, "login.html",
                       error="Usuario o clave incorrectos")
    respuesta = RedirectResponse("/", status_code=303)
    respuesta.set_cookie(
        COOKIE,
        firmante.dumps({"id": usuario.id, "nombre": usuario.nombre_completo,
                        "rol": usuario.rol}),
        httponly=True, samesite="lax")
    return respuesta


@router.get("/logout")
def logout():
    respuesta = RedirectResponse("/login", status_code=303)
    respuesta.delete_cookie(COOKIE)
    return respuesta


# ----------------------------------------------------------------- panel ---
@router.get("/", response_class=HTMLResponse)
def panel(request: Request, sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    return _render(request, "panel.html",
                   resumen=servicios.resumen(sesion),
                   mas_prestados=servicios.libros_mas_prestados(sesion),
                   vencidos=servicios.listar_prestamos(sesion, "vencidos"))


# ---------------------------------------------------------------- libros ---
@router.get("/libros", response_class=HTMLResponse)
def pagina_libros(request: Request, q: str = "", categoria: str = "",
                  mensaje: str = "", error: str = "",
                  sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    return _render(request, "libros.html",
                   libros=servicios.listar_libros(sesion, q, categoria),
                   categorias=servicios.categorias(sesion),
                   q=q, categoria_activa=categoria,
                   mensaje=mensaje, error=error)


@router.post("/libros")
def crear_libro_web(request: Request, isbn: str = Form(...),
                    titulo: str = Form(...), autor: str = Form(...),
                    categoria: str = Form("General"), anio: int = Form(0),
                    ejemplares: int = Form(1),
                    sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    try:
        servicios.crear_libro(sesion, dict(
            isbn=isbn.strip(), titulo=titulo.strip(), autor=autor.strip(),
            categoria=categoria.strip() or "General", anio=anio,
            ejemplares=ejemplares))
        destino = f"/libros?mensaje=Libro+'{titulo.strip()}'+registrado"
    except ReglaNegocioError as exc:
        destino = f"/libros?error={str(exc).replace(' ', '+')}"
    return RedirectResponse(destino, status_code=303)


@router.post("/libros/{libro_id}/eliminar")
def eliminar_libro_web(libro_id: int, request: Request,
                       sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    try:
        servicios.eliminar_libro(sesion, libro_id)
        destino = "/libros?mensaje=Libro+eliminado"
    except ReglaNegocioError as exc:
        destino = f"/libros?error={str(exc).replace(' ', '+')}"
    return RedirectResponse(destino, status_code=303)


# ---------------------------------------------------------------- socios ---
@router.get("/socios", response_class=HTMLResponse)
def pagina_socios(request: Request, q: str = "", mensaje: str = "",
                  error: str = "", sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    socios = servicios.listar_socios(sesion, q)
    activos = {s.id: servicios.prestamos_activos_de(sesion, s.id) for s in socios}
    return _render(request, "socios.html", socios=socios, activos=activos,
                   q=q, mensaje=mensaje, error=error)


@router.post("/socios")
def crear_socio_web(request: Request, matricula: str = Form(...),
                    nombre: str = Form(...), correo: str = Form(...),
                    telefono: str = Form(""),
                    sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    try:
        servicios.crear_socio(sesion, dict(
            matricula=matricula.strip(), nombre=nombre.strip(),
            correo=correo.strip(), telefono=telefono.strip()))
        destino = "/socios?mensaje=Socio+registrado"
    except ReglaNegocioError as exc:
        destino = f"/socios?error={str(exc).replace(' ', '+')}"
    return RedirectResponse(destino, status_code=303)


# ------------------------------------------------------------- prestamos ---
@router.get("/prestamos", response_class=HTMLResponse)
def pagina_prestamos(request: Request, estado: str = "activos",
                     mensaje: str = "", error: str = "",
                     sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    return _render(request, "prestamos.html",
                   prestamos=servicios.listar_prestamos(sesion, estado),
                   socios=servicios.listar_socios(sesion),
                   libros=servicios.listar_libros(sesion),
                   estado=estado, mensaje=mensaje, error=error)


@router.post("/prestamos")
def crear_prestamo_web(request: Request, socio_id: int = Form(...),
                       libro_id: int = Form(...),
                       sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    try:
        servicios.registrar_prestamo(sesion, socio_id, libro_id)
        destino = "/prestamos?mensaje=Prestamo+registrado+correctamente"
    except ReglaNegocioError as exc:
        destino = f"/prestamos?error={str(exc).replace(' ', '+')}"
    return RedirectResponse(destino, status_code=303)


@router.post("/prestamos/{prestamo_id}/devolver")
def devolver_web(prestamo_id: int, request: Request,
                 sesion: Session = Depends(obtener_sesion)):
    if not _exigir_sesion(request):
        return RedirectResponse("/login", status_code=303)
    try:
        prestamo = servicios.registrar_devolucion(sesion, prestamo_id)
        texto = "Devolucion+registrada"
        if prestamo.mora:
            texto += f".+Mora+cobrada:+RD$+{prestamo.mora}"
        destino = f"/prestamos?mensaje={texto}"
    except ReglaNegocioError as exc:
        destino = f"/prestamos?error={str(exc).replace(' ', '+')}"
    return RedirectResponse(destino, status_code=303)
