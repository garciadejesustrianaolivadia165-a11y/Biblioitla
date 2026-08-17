"""
Reglas de negocio de la biblioteca.

Estan aisladas a proposito, como funciones puras que no tocan la base de
datos: son el nucleo que se valida con las pruebas unitarias. La capa de
servicios (servicios.py) las invoca despues de consultar los datos.
"""

from datetime import date, timedelta

# Politicas de la biblioteca (parametros del negocio)
DIAS_PRESTAMO = 14          # duracion de un prestamo
MAX_PRESTAMOS_ACTIVOS = 3   # libros que un socio puede tener a la vez
MORA_POR_DIA = 25           # RD$ por cada dia de retraso


class ReglaNegocioError(Exception):
    """Se incumple una politica de la biblioteca (no es un fallo tecnico)."""


def calcular_vencimiento(fecha_prestamo: date,
                         dias: int = DIAS_PRESTAMO) -> date:
    """Fecha limite de devolucion."""
    if dias <= 0:
        raise ValueError("La duracion del prestamo debe ser mayor que cero")
    return fecha_prestamo + timedelta(days=dias)


def calcular_mora(fecha_vencimiento: date, fecha_devolucion: date,
                  tarifa: int = MORA_POR_DIA) -> int:
    """
    Mora en pesos. Devolver el mismo dia del vencimiento o antes no genera
    cargo; a partir del dia siguiente se cobra `tarifa` por dia de retraso.
    """
    dias_retraso = (fecha_devolucion - fecha_vencimiento).days
    return dias_retraso * tarifa if dias_retraso > 0 else 0


def validar_prestamo(socio_activo: bool, ejemplares_disponibles: int,
                     prestamos_activos_del_socio: int,
                     ya_tiene_este_libro: bool) -> None:
    """
    Comprueba las cuatro condiciones para entregar un ejemplar.
    Lanza ReglaNegocioError con el motivo; si no lanza, el prestamo procede.
    """
    if not socio_activo:
        raise ReglaNegocioError(
            "El socio esta inactivo y no puede tomar prestamos")
    if ejemplares_disponibles <= 0:
        raise ReglaNegocioError(
            "No hay ejemplares disponibles de este libro")
    if prestamos_activos_del_socio >= MAX_PRESTAMOS_ACTIVOS:
        raise ReglaNegocioError(
            f"El socio ya tiene {MAX_PRESTAMOS_ACTIVOS} prestamos activos, "
            f"que es el maximo permitido")
    if ya_tiene_este_libro:
        raise ReglaNegocioError(
            "El socio ya tiene un ejemplar de este libro sin devolver")


def validar_devolucion(prestamo_activo: bool) -> None:
    """Un prestamo ya cerrado no se puede devolver otra vez."""
    if not prestamo_activo:
        raise ReglaNegocioError("Este prestamo ya fue devuelto")


def validar_ejemplares(ejemplares: int, prestados: int) -> None:
    """No se puede reducir el inventario por debajo de lo que esta prestado."""
    if ejemplares < 0:
        raise ReglaNegocioError("El numero de ejemplares no puede ser negativo")
    if ejemplares < prestados:
        raise ReglaNegocioError(
            f"Hay {prestados} ejemplares prestados: no se puede dejar el "
            f"inventario en {ejemplares}")
