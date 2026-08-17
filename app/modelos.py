"""
Modelos de datos de BiblioITLA (SQLAlchemy 2.0).

Cuatro entidades:
    Usuario   - quien opera el sistema (bibliotecario / administrador)
    Socio     - la persona que toma libros prestados
    Libro     - el titulo, con un numero de ejemplares
    Prestamo  - relaciona un socio con un libro durante un periodo
"""

from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, String,
                        UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    """Operador del sistema. Se autentica para poder registrar prestamos."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre_usuario: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nombre_completo: Mapped[str] = mapped_column(String(120))
    clave_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), default="bibliotecario")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class Socio(Base):
    """Persona registrada que puede tomar libros prestados."""

    __tablename__ = "socios"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(120))
    telefono: Mapped[str] = mapped_column(String(30), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_registro: Mapped[date] = mapped_column(Date, default=date.today)

    prestamos: Mapped[list["Prestamo"]] = relationship(back_populates="socio")


class Libro(Base):
    """Titulo del catalogo. `ejemplares` es cuantas copias posee la biblioteca."""

    __tablename__ = "libros"

    id: Mapped[int] = mapped_column(primary_key=True)
    isbn: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200), index=True)
    autor: Mapped[str] = mapped_column(String(120), index=True)
    categoria: Mapped[str] = mapped_column(String(60), default="General")
    anio: Mapped[int] = mapped_column(Integer, default=0)
    ejemplares: Mapped[int] = mapped_column(Integer, default=1)

    prestamos: Mapped[list["Prestamo"]] = relationship(back_populates="libro")

    @property
    def prestados(self) -> int:
        """Ejemplares actualmente fuera de la biblioteca."""
        return sum(1 for p in self.prestamos if p.fecha_devolucion is None)

    @property
    def disponibles(self) -> int:
        return self.ejemplares - self.prestados


class Prestamo(Base):
    """Un ejemplar entregado a un socio. Se cierra al fijar fecha_devolucion."""

    __tablename__ = "prestamos"
    __table_args__ = (
        UniqueConstraint("socio_id", "libro_id", "fecha_devolucion",
                         name="uq_prestamo_activo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    socio_id: Mapped[int] = mapped_column(ForeignKey("socios.id"), index=True)
    libro_id: Mapped[int] = mapped_column(ForeignKey("libros.id"), index=True)
    fecha_prestamo: Mapped[date] = mapped_column(Date, default=date.today)
    fecha_vencimiento: Mapped[date] = mapped_column(Date)
    fecha_devolucion: Mapped[date | None] = mapped_column(Date, nullable=True)
    mora: Mapped[int] = mapped_column(Integer, default=0)
    registrado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    socio: Mapped["Socio"] = relationship(back_populates="prestamos")
    libro: Mapped["Libro"] = relationship(back_populates="prestamos")

    @property
    def activo(self) -> bool:
        return self.fecha_devolucion is None

    def esta_vencido(self, hoy: date | None = None) -> bool:
        """Un prestamo esta vencido si sigue abierto y ya paso su vencimiento."""
        hoy = hoy or date.today()
        return self.fecha_devolucion is None and hoy > self.fecha_vencimiento
