"""Esquemas Pydantic: validan la entrada y dan forma a la salida de la API."""

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LibroBase(BaseModel):
    isbn: str = Field(min_length=10, max_length=20)
    titulo: str = Field(min_length=1, max_length=200)
    autor: str = Field(min_length=1, max_length=120)
    categoria: str = Field(default="General", max_length=60)
    anio: int = Field(default=0, ge=0, le=2100)
    ejemplares: int = Field(default=1, ge=1, le=999)

    @field_validator("isbn", "titulo", "autor")
    @classmethod
    def sin_espacios_sobrantes(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El campo no puede estar vacio")
        return v


class LibroCrear(LibroBase):
    pass


class LibroActualizar(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    autor: str | None = Field(default=None, min_length=1, max_length=120)
    categoria: str | None = None
    anio: int | None = Field(default=None, ge=0, le=2100)
    ejemplares: int | None = Field(default=None, ge=0, le=999)


class LibroSalida(LibroBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    disponibles: int
    prestados: int


class SocioCrear(BaseModel):
    matricula: str = Field(min_length=4, max_length=20)
    nombre: str = Field(min_length=3, max_length=120)
    correo: EmailStr
    telefono: str = Field(default="", max_length=30)


class SocioActualizar(BaseModel):
    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    correo: EmailStr | None = None
    telefono: str | None = None
    activo: bool | None = None


class SocioSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matricula: str
    nombre: str
    correo: str
    telefono: str
    activo: bool
    fecha_registro: date


class PrestamoCrear(BaseModel):
    socio_id: int = Field(gt=0)
    libro_id: int = Field(gt=0)


class PrestamoSalida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    socio_id: int
    libro_id: int
    fecha_prestamo: date
    fecha_vencimiento: date
    fecha_devolucion: date | None
    mora: int
    activo: bool


class Credenciales(BaseModel):
    nombre_usuario: str
    clave: str
