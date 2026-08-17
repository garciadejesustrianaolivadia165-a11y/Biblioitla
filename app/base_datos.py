"""
Conexion a la base de datos y datos iniciales.

La URL sale de la variable de entorno BIBLIOITLA_DB, lo que permite que las
pruebas usen una base aparte (o en memoria) sin tocar la de desarrollo.
"""

import hashlib
import os
import secrets
from datetime import date, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from .modelos import Base, Libro, Prestamo, Socio, Usuario
from .reglas import calcular_vencimiento

URL_BD = os.environ.get("BIBLIOITLA_DB", "sqlite:///./biblioitla.db")

motor = create_engine(
    URL_BD,
    connect_args={"check_same_thread": False} if URL_BD.startswith("sqlite") else {},
)
SesionLocal = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


def obtener_sesion():
    """Dependencia de FastAPI: una sesion por peticion."""
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


# --------------------------------------------------------------------------
# Claves
# --------------------------------------------------------------------------
def cifrar_clave(clave: str, sal: str | None = None) -> str:
    """PBKDF2-HMAC-SHA256. Se guarda como 'sal$hash'."""
    sal = sal or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", clave.encode(), sal.encode(), 120_000)
    return f"{sal}${dk.hex()}"


def verificar_clave(clave: str, almacenada: str) -> bool:
    try:
        sal, _ = almacenada.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(cifrar_clave(clave, sal), almacenada)


# --------------------------------------------------------------------------
# Creacion del esquema y datos de ejemplo
# --------------------------------------------------------------------------
def crear_tablas() -> None:
    Base.metadata.create_all(motor)


LIBROS_INICIALES = [
    ("978-0132350884", "Clean Code", "Robert C. Martin", "Ingenieria de Software", 2008, 3),
    ("978-0201616224", "The Pragmatic Programmer", "Andrew Hunt", "Ingenieria de Software", 1999, 2),
    ("978-0134685991", "Effective Java", "Joshua Bloch", "Programacion", 2018, 2),
    ("978-1449355739", "Learning Python", "Mark Lutz", "Programacion", 2013, 4),
    ("978-0596007126", "Head First Design Patterns", "Eric Freeman", "Arquitectura", 2004, 2),
    ("978-8499892726", "Cien anos de soledad", "Gabriel Garcia Marquez", "Literatura", 1967, 5),
    ("978-8437604947", "La casa de los espiritus", "Isabel Allende", "Literatura", 1982, 3),
    ("978-9945160123", "La Mananosa", "Juan Bosch", "Literatura dominicana", 1977, 4),
    ("978-1491950357", "Building Microservices", "Sam Newman", "Arquitectura", 2015, 2),
    ("978-0321125217", "Domain-Driven Design", "Eric Evans", "Arquitectura", 2003, 1),
]

SOCIOS_INICIALES = [
    ("20231395", "Triana Olivadia Garcia de Jesus", "20231395@itla.edu.do", "809-555-0101"),
    ("20231401", "Luis Manuel Perez", "20231401@itla.edu.do", "809-555-0102"),
    ("20231412", "Ana Cristina Rosario", "20231412@itla.edu.do", "809-555-0103"),
    ("20231428", "Jose Ramon Diaz", "20231428@itla.edu.do", "809-555-0104"),
    ("20231433", "Maria Fernanda Cruz", "20231433@itla.edu.do", "809-555-0105"),
]


def sembrar_datos(sesion: Session, con_prestamos: bool = True) -> None:
    """Carga el catalogo inicial. No hace nada si ya hay datos."""
    if sesion.scalar(select(Usuario).limit(1)) is None:
        sesion.add(Usuario(
            nombre_usuario="admin",
            nombre_completo="Bibliotecario Principal",
            clave_hash=cifrar_clave("BiblioITLA2026"),
            rol="administrador",
        ))

    if sesion.scalar(select(Libro).limit(1)) is None:
        for isbn, titulo, autor, cat, anio, ej in LIBROS_INICIALES:
            sesion.add(Libro(isbn=isbn, titulo=titulo, autor=autor,
                             categoria=cat, anio=anio, ejemplares=ej))

    if sesion.scalar(select(Socio).limit(1)) is None:
        for mat, nombre, correo, tel in SOCIOS_INICIALES:
            sesion.add(Socio(matricula=mat, nombre=nombre, correo=correo,
                             telefono=tel))
    sesion.commit()

    if con_prestamos and sesion.scalar(select(Prestamo).limit(1)) is None:
        socio = sesion.scalar(select(Socio).where(Socio.matricula == "20231401"))
        libro = sesion.scalar(select(Libro).where(Libro.titulo == "Clean Code"))
        vencido = sesion.scalar(select(Libro).where(Libro.titulo == "Effective Java"))
        hoy = date.today()
        if socio and libro:
            sesion.add(Prestamo(socio_id=socio.id, libro_id=libro.id,
                                fecha_prestamo=hoy - timedelta(days=3),
                                fecha_vencimiento=calcular_vencimiento(
                                    hoy - timedelta(days=3))))
        if socio and vencido:   # un prestamo ya vencido, para ver la alerta
            sesion.add(Prestamo(socio_id=socio.id, libro_id=vencido.id,
                                fecha_prestamo=hoy - timedelta(days=20),
                                fecha_vencimiento=calcular_vencimiento(
                                    hoy - timedelta(days=20))))
        sesion.commit()


def inicializar(con_prestamos: bool = True) -> None:
    crear_tablas()
    with SesionLocal() as sesion:
        sembrar_datos(sesion, con_prestamos=con_prestamos)
