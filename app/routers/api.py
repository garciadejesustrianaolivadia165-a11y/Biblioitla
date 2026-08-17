"""API REST de BiblioITLA (prefijo /api)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import esquemas, servicios
from ..base_datos import obtener_sesion
from ..reglas import ReglaNegocioError

router = APIRouter(prefix="/api", tags=["api"])


def _error(exc: ReglaNegocioError) -> HTTPException:
    """Una regla de negocio incumplida es un 409, no un 500."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ---------------------------------------------------------------- libros ---
@router.get("/libros", response_model=list[esquemas.LibroSalida])
def listar_libros(busqueda: str = Query("", alias="q"), categoria: str = "",
                  sesion: Session = Depends(obtener_sesion)):
    return servicios.listar_libros(sesion, busqueda, categoria)


@router.get("/libros/{libro_id}", response_model=esquemas.LibroSalida)
def obtener_libro(libro_id: int, sesion: Session = Depends(obtener_sesion)):
    libro = servicios.obtener_libro(sesion, libro_id)
    if libro is None:
        raise HTTPException(status_code=404, detail="El libro no existe")
    return libro


@router.post("/libros", response_model=esquemas.LibroSalida, status_code=201)
def crear_libro(datos: esquemas.LibroCrear,
                sesion: Session = Depends(obtener_sesion)):
    try:
        return servicios.crear_libro(sesion, datos.model_dump())
    except ReglaNegocioError as exc:
        raise _error(exc)


@router.put("/libros/{libro_id}", response_model=esquemas.LibroSalida)
def actualizar_libro(libro_id: int, datos: esquemas.LibroActualizar,
                     sesion: Session = Depends(obtener_sesion)):
    cambios = datos.model_dump(exclude_none=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="No se envio ningun campo")
    try:
        return servicios.actualizar_libro(sesion, libro_id, cambios)
    except ReglaNegocioError as exc:
        if "no existe" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc))
        raise _error(exc)


@router.delete("/libros/{libro_id}", status_code=204)
def eliminar_libro(libro_id: int, sesion: Session = Depends(obtener_sesion)):
    try:
        servicios.eliminar_libro(sesion, libro_id)
    except ReglaNegocioError as exc:
        if "no existe" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc))
        raise _error(exc)


# ---------------------------------------------------------------- socios ---
@router.get("/socios", response_model=list[esquemas.SocioSalida])
def listar_socios(busqueda: str = Query("", alias="q"),
                  sesion: Session = Depends(obtener_sesion)):
    return servicios.listar_socios(sesion, busqueda)


@router.post("/socios", response_model=esquemas.SocioSalida, status_code=201)
def crear_socio(datos: esquemas.SocioCrear,
                sesion: Session = Depends(obtener_sesion)):
    try:
        return servicios.crear_socio(sesion, datos.model_dump())
    except ReglaNegocioError as exc:
        raise _error(exc)


@router.put("/socios/{socio_id}", response_model=esquemas.SocioSalida)
def actualizar_socio(socio_id: int, datos: esquemas.SocioActualizar,
                     sesion: Session = Depends(obtener_sesion)):
    cambios = datos.model_dump(exclude_none=True)
    if not cambios:
        raise HTTPException(status_code=400, detail="No se envio ningun campo")
    try:
        return servicios.actualizar_socio(sesion, socio_id, cambios)
    except ReglaNegocioError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ------------------------------------------------------------- prestamos ---
@router.get("/prestamos", response_model=list[esquemas.PrestamoSalida])
def listar_prestamos(estado: str = "todos",
                     sesion: Session = Depends(obtener_sesion)):
    return servicios.listar_prestamos(sesion, estado)


@router.post("/prestamos", response_model=esquemas.PrestamoSalida, status_code=201)
def registrar_prestamo(datos: esquemas.PrestamoCrear,
                       sesion: Session = Depends(obtener_sesion)):
    try:
        return servicios.registrar_prestamo(sesion, datos.socio_id, datos.libro_id)
    except ReglaNegocioError as exc:
        if "no existe" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc))
        raise _error(exc)


@router.post("/prestamos/{prestamo_id}/devolucion",
             response_model=esquemas.PrestamoSalida)
def registrar_devolucion(prestamo_id: int,
                         sesion: Session = Depends(obtener_sesion)):
    try:
        return servicios.registrar_devolucion(sesion, prestamo_id)
    except ReglaNegocioError as exc:
        if "no existe" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc))
        raise _error(exc)


# -------------------------------------------------------------- reportes ---
@router.get("/reportes/resumen")
def reporte_resumen(sesion: Session = Depends(obtener_sesion)):
    return servicios.resumen(sesion)


@router.get("/reportes/mas-prestados")
def reporte_mas_prestados(limite: int = 5,
                          sesion: Session = Depends(obtener_sesion)):
    return servicios.libros_mas_prestados(sesion, limite)


# ---------------------------------------------------------------- sesion ---
@router.post("/login")
def login(datos: esquemas.Credenciales,
          sesion: Session = Depends(obtener_sesion)):
    usuario = servicios.autenticar(sesion, datos.nombre_usuario, datos.clave)
    if usuario is None:
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    return {"id": usuario.id, "nombre": usuario.nombre_completo,
            "rol": usuario.rol}


@router.get("/salud")
def salud():
    return {"estado": "ok", "servicio": "BiblioITLA", "version": "1.0.0"}
