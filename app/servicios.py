"""
Capa de servicios: consulta la base de datos, aplica las reglas de negocio
(reglas.py) y persiste el resultado.

Los routers no hablan con los modelos directamente; pasan por aqui. Asi la
logica se puede probar sin levantar el servidor HTTP.
"""

from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .modelos import Libro, Prestamo, Socio, Usuario
from .reglas import (ReglaNegocioError, calcular_mora, calcular_vencimiento,
                     validar_devolucion, validar_ejemplares, validar_prestamo)


# ==========================================================================
# Libros
# ==========================================================================
def listar_libros(sesion: Session, busqueda: str = "",
                  categoria: str = "") -> list[Libro]:
    consulta = select(Libro)
    if busqueda:
        patron = f"%{busqueda.strip()}%"
        consulta = consulta.where(or_(Libro.titulo.ilike(patron),
                                      Libro.autor.ilike(patron),
                                      Libro.isbn.ilike(patron)))
    if categoria:
        consulta = consulta.where(Libro.categoria == categoria)
    return list(sesion.scalars(consulta.order_by(Libro.titulo)))


def obtener_libro(sesion: Session, libro_id: int) -> Libro | None:
    return sesion.get(Libro, libro_id)


def crear_libro(sesion: Session, datos: dict) -> Libro:
    if sesion.scalar(select(Libro).where(Libro.isbn == datos["isbn"])):
        raise ReglaNegocioError(f"Ya existe un libro con el ISBN {datos['isbn']}")
    if int(datos.get("ejemplares", 1)) < 1:
        raise ReglaNegocioError("Debe registrarse al menos un ejemplar")
    libro = Libro(**datos)
    sesion.add(libro)
    sesion.commit()
    sesion.refresh(libro)
    return libro


def actualizar_libro(sesion: Session, libro_id: int, datos: dict) -> Libro:
    libro = sesion.get(Libro, libro_id)
    if libro is None:
        raise ReglaNegocioError("El libro no existe")
    if "ejemplares" in datos:
        validar_ejemplares(int(datos["ejemplares"]), libro.prestados)
    if "isbn" in datos and datos["isbn"] != libro.isbn:
        if sesion.scalar(select(Libro).where(Libro.isbn == datos["isbn"])):
            raise ReglaNegocioError(f"Ya existe un libro con el ISBN {datos['isbn']}")
    for campo, valor in datos.items():
        setattr(libro, campo, valor)
    sesion.commit()
    sesion.refresh(libro)
    return libro


def eliminar_libro(sesion: Session, libro_id: int) -> None:
    libro = sesion.get(Libro, libro_id)
    if libro is None:
        raise ReglaNegocioError("El libro no existe")
    if libro.prestados > 0:
        raise ReglaNegocioError(
            "No se puede eliminar un libro con ejemplares prestados")
    sesion.delete(libro)
    sesion.commit()


def categorias(sesion: Session) -> list[str]:
    return list(sesion.scalars(select(Libro.categoria).distinct()
                               .order_by(Libro.categoria)))


# ==========================================================================
# Socios
# ==========================================================================
def listar_socios(sesion: Session, busqueda: str = "") -> list[Socio]:
    consulta = select(Socio)
    if busqueda:
        patron = f"%{busqueda.strip()}%"
        consulta = consulta.where(or_(Socio.nombre.ilike(patron),
                                      Socio.matricula.ilike(patron),
                                      Socio.correo.ilike(patron)))
    return list(sesion.scalars(consulta.order_by(Socio.nombre)))


def crear_socio(sesion: Session, datos: dict) -> Socio:
    if sesion.scalar(select(Socio).where(Socio.matricula == datos["matricula"])):
        raise ReglaNegocioError(
            f"Ya existe un socio con la matricula {datos['matricula']}")
    socio = Socio(**datos)
    sesion.add(socio)
    sesion.commit()
    sesion.refresh(socio)
    return socio


def actualizar_socio(sesion: Session, socio_id: int, datos: dict) -> Socio:
    socio = sesion.get(Socio, socio_id)
    if socio is None:
        raise ReglaNegocioError("El socio no existe")
    for campo, valor in datos.items():
        setattr(socio, campo, valor)
    sesion.commit()
    sesion.refresh(socio)
    return socio


def prestamos_activos_de(sesion: Session, socio_id: int) -> int:
    return sesion.scalar(
        select(func.count(Prestamo.id))
        .where(Prestamo.socio_id == socio_id,
               Prestamo.fecha_devolucion.is_(None))) or 0


# ==========================================================================
# Prestamos
# ==========================================================================
def registrar_prestamo(sesion: Session, socio_id: int, libro_id: int,
                       hoy: date | None = None) -> Prestamo:
    """Entrega un ejemplar tras comprobar las cuatro reglas del negocio."""
    hoy = hoy or date.today()
    socio = sesion.get(Socio, socio_id)
    libro = sesion.get(Libro, libro_id)
    if socio is None:
        raise ReglaNegocioError("El socio no existe")
    if libro is None:
        raise ReglaNegocioError("El libro no existe")

    ya_lo_tiene = sesion.scalar(
        select(Prestamo).where(Prestamo.socio_id == socio_id,
                               Prestamo.libro_id == libro_id,
                               Prestamo.fecha_devolucion.is_(None))) is not None

    validar_prestamo(
        socio_activo=socio.activo,
        ejemplares_disponibles=libro.disponibles,
        prestamos_activos_del_socio=prestamos_activos_de(sesion, socio_id),
        ya_tiene_este_libro=ya_lo_tiene,
    )

    prestamo = Prestamo(socio_id=socio_id, libro_id=libro_id,
                        fecha_prestamo=hoy,
                        fecha_vencimiento=calcular_vencimiento(hoy))
    sesion.add(prestamo)
    sesion.commit()
    sesion.refresh(prestamo)
    return prestamo


def registrar_devolucion(sesion: Session, prestamo_id: int,
                         hoy: date | None = None) -> Prestamo:
    """Cierra el prestamo y calcula la mora si hubo retraso."""
    hoy = hoy or date.today()
    prestamo = sesion.get(Prestamo, prestamo_id)
    if prestamo is None:
        raise ReglaNegocioError("El prestamo no existe")

    validar_devolucion(prestamo.activo)

    prestamo.fecha_devolucion = hoy
    prestamo.mora = calcular_mora(prestamo.fecha_vencimiento, hoy)
    sesion.commit()
    sesion.refresh(prestamo)
    return prestamo


def listar_prestamos(sesion: Session, estado: str = "todos") -> list[Prestamo]:
    consulta = select(Prestamo)
    if estado == "activos":
        consulta = consulta.where(Prestamo.fecha_devolucion.is_(None))
    elif estado == "devueltos":
        consulta = consulta.where(Prestamo.fecha_devolucion.is_not(None))
    elif estado == "vencidos":
        consulta = consulta.where(Prestamo.fecha_devolucion.is_(None),
                                  Prestamo.fecha_vencimiento < date.today())
    return list(sesion.scalars(consulta.order_by(Prestamo.id.desc())))


# ==========================================================================
# Reportes
# ==========================================================================
def resumen(sesion: Session) -> dict:
    """Indicadores del panel principal."""
    total_libros = sesion.scalar(select(func.count(Libro.id))) or 0
    ejemplares = sesion.scalar(select(func.sum(Libro.ejemplares))) or 0
    activos = sesion.scalar(
        select(func.count(Prestamo.id))
        .where(Prestamo.fecha_devolucion.is_(None))) or 0
    vencidos = sesion.scalar(
        select(func.count(Prestamo.id))
        .where(Prestamo.fecha_devolucion.is_(None),
               Prestamo.fecha_vencimiento < date.today())) or 0
    socios = sesion.scalar(
        select(func.count(Socio.id)).where(Socio.activo.is_(True))) or 0
    mora = sesion.scalar(select(func.sum(Prestamo.mora))) or 0
    return {
        "titulos": total_libros,
        "ejemplares": int(ejemplares),
        "disponibles": int(ejemplares) - activos,
        "prestamos_activos": activos,
        "prestamos_vencidos": vencidos,
        "socios_activos": socios,
        "mora_acumulada": int(mora),
    }


def libros_mas_prestados(sesion: Session, limite: int = 5) -> list[dict]:
    filas = sesion.execute(
        select(Libro.titulo, Libro.autor, func.count(Prestamo.id).label("veces"))
        .join(Prestamo, Prestamo.libro_id == Libro.id)
        .group_by(Libro.id)
        .order_by(func.count(Prestamo.id).desc())
        .limit(limite)).all()
    return [{"titulo": t, "autor": a, "veces": v} for t, a, v in filas]


# ==========================================================================
# Autenticacion
# ==========================================================================
def autenticar(sesion: Session, nombre_usuario: str, clave: str) -> Usuario | None:
    from .base_datos import verificar_clave
    usuario = sesion.scalar(
        select(Usuario).where(Usuario.nombre_usuario == nombre_usuario))
    if usuario and usuario.activo and verificar_clave(clave, usuario.clave_hash):
        return usuario
    return None
