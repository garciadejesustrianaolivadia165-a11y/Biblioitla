"""
Pruebas de integracion del circuito de prestamos y devoluciones, que es el
nucleo del sistema: aqui se comprueba que las reglas de negocio se aplican de
verdad a traves de la API y que el inventario queda consistente.

Trazabilidad: RF-04, RF-05, RF-06, RF-07, RF-10  |  HU-04..HU-08
"""

from datetime import date, timedelta

import pytest

from app.reglas import DIAS_PRESTAMO, MAX_PRESTAMOS_ACTIVOS, MORA_POR_DIA


def prestar(cliente, socio_id=1, libro_id=1):
    return cliente.post("/api/prestamos",
                        json={"socio_id": socio_id, "libro_id": libro_id})


class TestRegistrarPrestamo:
    """RF-05 / HU-04."""

    def test_registra_y_devuelve_201(self, cliente):
        r = prestar(cliente)
        assert r.status_code == 201
        assert r.json()["activo"] is True
        assert r.json()["fecha_devolucion"] is None

    def test_calcula_el_vencimiento_a_14_dias(self, cliente):
        cuerpo = prestar(cliente).json()
        prestamo = date.fromisoformat(cuerpo["fecha_prestamo"])
        vence = date.fromisoformat(cuerpo["fecha_vencimiento"])
        assert (vence - prestamo).days == DIAS_PRESTAMO

    def test_descuenta_un_ejemplar_disponible(self, cliente):
        antes = cliente.get("/api/libros/1").json()["disponibles"]
        prestar(cliente)
        despues = cliente.get("/api/libros/1").json()["disponibles"]
        assert despues == antes - 1

    def test_socio_inexistente_da_404(self, cliente):
        assert prestar(cliente, socio_id=9999).status_code == 404

    def test_libro_inexistente_da_404(self, cliente):
        assert prestar(cliente, libro_id=9999).status_code == 404

    def test_rechaza_ids_no_positivos(self, cliente):
        assert prestar(cliente, socio_id=0).status_code == 422

    def test_no_presta_el_mismo_libro_dos_veces_al_mismo_socio(self, cliente):
        prestar(cliente)
        r = prestar(cliente)
        assert r.status_code == 409
        assert "sin devolver" in r.json()["detail"]

    def test_no_presta_si_no_quedan_ejemplares(self, cliente):
        """'Domain-Driven Design' (id 10) tiene un unico ejemplar."""
        libro = next(l for l in cliente.get("/api/libros").json()
                     if l["titulo"] == "Domain-Driven Design")
        assert libro["ejemplares"] == 1
        assert prestar(cliente, socio_id=1, libro_id=libro["id"]).status_code == 201
        r = prestar(cliente, socio_id=2, libro_id=libro["id"])
        assert r.status_code == 409
        assert "disponibles" in r.json()["detail"]

    def test_respeta_el_limite_de_prestamos_por_socio(self, cliente):
        for libro_id in range(1, MAX_PRESTAMOS_ACTIVOS + 1):
            assert prestar(cliente, libro_id=libro_id).status_code == 201
        r = prestar(cliente, libro_id=MAX_PRESTAMOS_ACTIVOS + 1)
        assert r.status_code == 409
        assert "maximo" in r.json()["detail"]

    def test_un_socio_inactivo_no_puede_pedir_prestado(self, cliente):
        cliente.put("/api/socios/1", json={"activo": False})
        r = prestar(cliente)
        assert r.status_code == 409 and "inactivo" in r.json()["detail"]

    def test_otro_socio_si_puede_llevarse_el_mismo_titulo(self, cliente):
        """Clean Code tiene 3 ejemplares: dos socios distintos pueden tenerlo."""
        assert prestar(cliente, socio_id=1, libro_id=1).status_code == 201
        assert prestar(cliente, socio_id=2, libro_id=1).status_code == 201


class TestDevolucion:
    """RF-06 / HU-05, HU-06."""

    def test_cierra_el_prestamo(self, cliente):
        pid = prestar(cliente).json()["id"]
        r = cliente.post(f"/api/prestamos/{pid}/devolucion")
        assert r.status_code == 200
        assert r.json()["activo"] is False
        assert r.json()["fecha_devolucion"] == date.today().isoformat()

    def test_devuelve_el_ejemplar_al_inventario(self, cliente):
        antes = cliente.get("/api/libros/1").json()["disponibles"]
        pid = prestar(cliente).json()["id"]
        cliente.post(f"/api/prestamos/{pid}/devolucion")
        assert cliente.get("/api/libros/1").json()["disponibles"] == antes

    def test_devolver_a_tiempo_no_genera_mora(self, cliente):
        pid = prestar(cliente).json()["id"]
        r = cliente.post(f"/api/prestamos/{pid}/devolucion")
        assert r.json()["mora"] == 0

    def test_no_se_puede_devolver_dos_veces(self, cliente):
        pid = prestar(cliente).json()["id"]
        cliente.post(f"/api/prestamos/{pid}/devolucion")
        r = cliente.post(f"/api/prestamos/{pid}/devolucion")
        assert r.status_code == 409 and "ya fue devuelto" in r.json()["detail"]

    def test_prestamo_inexistente_da_404(self, cliente):
        assert cliente.post("/api/prestamos/9999/devolucion").status_code == 404

    def test_tras_devolver_se_puede_volver_a_prestar(self, cliente):
        pid = prestar(cliente).json()["id"]
        cliente.post(f"/api/prestamos/{pid}/devolucion")
        assert prestar(cliente).status_code == 201


class TestMoraPorRetraso:
    """RF-06: la mora se calcula al cerrar un prestamo vencido."""

    def test_cobra_la_mora_de_un_prestamo_vencido(self, cliente, fabrica_sesiones):
        from app.modelos import Prestamo

        pid = prestar(cliente).json()["id"]
        # Se envejece el prestamo 5 dias mas alla de su vencimiento
        with fabrica_sesiones() as s:
            p = s.get(Prestamo, pid)
            p.fecha_vencimiento = date.today() - timedelta(days=5)
            s.commit()

        r = cliente.post(f"/api/prestamos/{pid}/devolucion")
        assert r.status_code == 200
        assert r.json()["mora"] == 5 * MORA_POR_DIA


class TestConsultarPrestamos:
    """RF-07 / HU-07: filtrar por estado."""

    def test_lista_vacia_al_inicio(self, cliente):
        assert cliente.get("/api/prestamos").json() == []

    def test_filtra_los_activos(self, cliente):
        prestar(cliente, libro_id=1)
        pid = prestar(cliente, libro_id=2).json()["id"]
        cliente.post(f"/api/prestamos/{pid}/devolucion")

        assert len(cliente.get("/api/prestamos",
                               params={"estado": "activos"}).json()) == 1
        assert len(cliente.get("/api/prestamos",
                               params={"estado": "devueltos"}).json()) == 1
        assert len(cliente.get("/api/prestamos",
                               params={"estado": "todos"}).json()) == 2

    def test_filtra_los_vencidos(self, cliente, fabrica_sesiones):
        from app.modelos import Prestamo

        pid = prestar(cliente).json()["id"]
        assert cliente.get("/api/prestamos",
                           params={"estado": "vencidos"}).json() == []

        with fabrica_sesiones() as s:
            s.get(Prestamo, pid).fecha_vencimiento = date.today() - timedelta(days=1)
            s.commit()

        assert len(cliente.get("/api/prestamos",
                               params={"estado": "vencidos"}).json()) == 1


class TestReportes:
    """RF-10 / HU-08: indicadores del panel."""

    def test_resumen_inicial(self, cliente):
        r = cliente.get("/api/reportes/resumen").json()
        assert r["titulos"] == 10
        assert r["prestamos_activos"] == 0
        assert r["socios_activos"] == 5
        assert r["disponibles"] == r["ejemplares"]

    def test_el_resumen_refleja_un_prestamo(self, cliente):
        prestar(cliente)
        r = cliente.get("/api/reportes/resumen").json()
        assert r["prestamos_activos"] == 1
        assert r["disponibles"] == r["ejemplares"] - 1

    def test_libros_mas_prestados(self, cliente):
        prestar(cliente, socio_id=1, libro_id=1)
        prestar(cliente, socio_id=2, libro_id=1)
        prestar(cliente, socio_id=3, libro_id=2)

        top = cliente.get("/api/reportes/mas-prestados").json()
        assert top[0]["titulo"] == "Clean Code"
        assert top[0]["veces"] == 2

    @pytest.mark.parametrize("limite", [1, 3])
    def test_respeta_el_limite_pedido(self, cliente, limite):
        for libro_id in (1, 2, 3):
            prestar(cliente, socio_id=libro_id, libro_id=libro_id)
        top = cliente.get("/api/reportes/mas-prestados",
                          params={"limite": limite}).json()
        assert len(top) == limite
