"""
Pruebas unitarias de las reglas de negocio (app/reglas.py).

Son funciones puras: no hay base de datos ni servidor, asi que cada prueba
comprueba una sola politica de la biblioteca de forma aislada.

Trazabilidad: RF-04, RF-05, RF-06, RF-07  |  HU-04, HU-05, HU-06
"""

from datetime import date

import pytest

from app.reglas import (DIAS_PRESTAMO, MAX_PRESTAMOS_ACTIVOS, MORA_POR_DIA,
                        ReglaNegocioError, calcular_mora, calcular_vencimiento,
                        validar_devolucion, validar_ejemplares, validar_prestamo)


# =========================================================== vencimiento ===
class TestCalcularVencimiento:
    """RF-04: el prestamo vence 14 dias despues de la entrega."""

    def test_suma_los_dias_de_politica(self):
        assert calcular_vencimiento(date(2026, 3, 1)) == date(2026, 3, 15)

    def test_usa_la_politica_de_14_dias(self):
        inicio = date(2026, 1, 10)
        assert (calcular_vencimiento(inicio) - inicio).days == DIAS_PRESTAMO

    def test_cruza_correctamente_el_cambio_de_mes(self):
        assert calcular_vencimiento(date(2026, 1, 25)) == date(2026, 2, 8)

    def test_cruza_correctamente_el_cambio_de_anio(self):
        assert calcular_vencimiento(date(2025, 12, 26)) == date(2026, 1, 9)

    def test_anio_bisiesto(self):
        # 2028 es bisiesto: del 20 de febrero + 14 dias = 5 de marzo
        assert calcular_vencimiento(date(2028, 2, 20)) == date(2028, 3, 5)

    def test_permite_un_plazo_personalizado(self):
        assert calcular_vencimiento(date(2026, 3, 1), dias=7) == date(2026, 3, 8)

    @pytest.mark.parametrize("dias", [0, -1, -30])
    def test_rechaza_plazos_no_positivos(self, dias):
        with pytest.raises(ValueError):
            calcular_vencimiento(date(2026, 3, 1), dias=dias)


# ================================================================== mora ===
class TestCalcularMora:
    """RF-06: RD$25 por cada dia de retraso; devolver a tiempo no cobra."""

    def test_devolucion_el_mismo_dia_del_vencimiento_no_cobra(self):
        assert calcular_mora(date(2026, 3, 15), date(2026, 3, 15)) == 0

    def test_devolucion_anticipada_no_cobra(self):
        assert calcular_mora(date(2026, 3, 15), date(2026, 3, 10)) == 0

    def test_un_dia_de_retraso_cobra_la_tarifa(self):
        assert calcular_mora(date(2026, 3, 15), date(2026, 3, 16)) == MORA_POR_DIA

    def test_cinco_dias_de_retraso(self):
        assert calcular_mora(date(2026, 3, 15), date(2026, 3, 20)) == 5 * MORA_POR_DIA

    def test_retraso_de_un_mes(self):
        assert calcular_mora(date(2026, 3, 1), date(2026, 3, 31)) == 30 * MORA_POR_DIA

    def test_respeta_una_tarifa_distinta(self):
        assert calcular_mora(date(2026, 3, 15), date(2026, 3, 18), tarifa=50) == 150

    def test_la_mora_nunca_es_negativa(self):
        assert calcular_mora(date(2026, 6, 1), date(2026, 1, 1)) == 0


# ====================================================== validar_prestamo ===
class TestValidarPrestamo:
    """RF-05: las cuatro condiciones para entregar un ejemplar."""

    CORRECTO = dict(socio_activo=True, ejemplares_disponibles=2,
                    prestamos_activos_del_socio=0, ya_tiene_este_libro=False)

    def test_caso_valido_no_lanza(self):
        validar_prestamo(**self.CORRECTO)          # no debe lanzar

    def test_rechaza_socio_inactivo(self):
        datos = self.CORRECTO | {"socio_activo": False}
        with pytest.raises(ReglaNegocioError, match="inactivo"):
            validar_prestamo(**datos)

    def test_rechaza_si_no_hay_ejemplares(self):
        datos = self.CORRECTO | {"ejemplares_disponibles": 0}
        with pytest.raises(ReglaNegocioError, match="disponibles"):
            validar_prestamo(**datos)

    def test_rechaza_disponibilidad_negativa(self):
        datos = self.CORRECTO | {"ejemplares_disponibles": -1}
        with pytest.raises(ReglaNegocioError):
            validar_prestamo(**datos)

    def test_permite_justo_debajo_del_limite(self):
        datos = self.CORRECTO | {
            "prestamos_activos_del_socio": MAX_PRESTAMOS_ACTIVOS - 1}
        validar_prestamo(**datos)

    def test_rechaza_al_alcanzar_el_limite(self):
        datos = self.CORRECTO | {
            "prestamos_activos_del_socio": MAX_PRESTAMOS_ACTIVOS}
        with pytest.raises(ReglaNegocioError, match="maximo"):
            validar_prestamo(**datos)

    def test_rechaza_el_mismo_libro_dos_veces(self):
        datos = self.CORRECTO | {"ya_tiene_este_libro": True}
        with pytest.raises(ReglaNegocioError, match="sin devolver"):
            validar_prestamo(**datos)

    def test_el_socio_inactivo_se_comprueba_primero(self):
        """Con varios problemas a la vez, el mensaje debe ser el del socio."""
        with pytest.raises(ReglaNegocioError, match="inactivo"):
            validar_prestamo(socio_activo=False, ejemplares_disponibles=0,
                             prestamos_activos_del_socio=99,
                             ya_tiene_este_libro=True)


# ==================================================== validar_devolucion ===
class TestValidarDevolucion:
    """RF-06: un prestamo cerrado no se puede devolver otra vez."""

    def test_acepta_un_prestamo_abierto(self):
        validar_devolucion(prestamo_activo=True)

    def test_rechaza_un_prestamo_ya_cerrado(self):
        with pytest.raises(ReglaNegocioError, match="ya fue devuelto"):
            validar_devolucion(prestamo_activo=False)


# ==================================================== validar_ejemplares ===
class TestValidarEjemplares:
    """RF-02: el inventario no puede quedar por debajo de lo prestado."""

    def test_acepta_un_inventario_mayor_que_lo_prestado(self):
        validar_ejemplares(ejemplares=5, prestados=2)

    def test_acepta_que_todo_este_prestado(self):
        validar_ejemplares(ejemplares=3, prestados=3)

    def test_rechaza_un_inventario_menor_que_lo_prestado(self):
        with pytest.raises(ReglaNegocioError, match="prestados"):
            validar_ejemplares(ejemplares=1, prestados=3)

    def test_rechaza_un_inventario_negativo(self):
        with pytest.raises(ReglaNegocioError, match="negativo"):
            validar_ejemplares(ejemplares=-1, prestados=0)
