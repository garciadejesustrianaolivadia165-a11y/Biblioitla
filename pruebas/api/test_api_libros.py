"""
Pruebas de integracion de la API de libros y socios.

Recorren la pila completa: HTTP -> validacion Pydantic -> servicios ->
reglas -> base de datos.

Trazabilidad: RF-01, RF-02, RF-03, RF-08  |  HU-01, HU-02, HU-03, HU-09
"""

LIBRO_NUEVO = {
    "isbn": "978-1111111111",
    "titulo": "Refactoring",
    "autor": "Martin Fowler",
    "categoria": "Ingenieria de Software",
    "anio": 2018,
    "ejemplares": 2,
}


class TestSalud:
    def test_el_servicio_responde(self, cliente):
        r = cliente.get("/api/salud")
        assert r.status_code == 200
        assert r.json()["estado"] == "ok"


class TestListarLibros:
    """RF-01 / HU-01: consultar el catalogo."""

    def test_devuelve_el_catalogo_inicial(self, cliente):
        r = cliente.get("/api/libros")
        assert r.status_code == 200
        assert len(r.json()) == 10

    def test_cada_libro_trae_su_disponibilidad(self, cliente):
        libro = cliente.get("/api/libros").json()[0]
        assert {"id", "isbn", "titulo", "disponibles", "prestados"} <= libro.keys()
        assert libro["disponibles"] == libro["ejemplares"]

    def test_busqueda_por_titulo(self, cliente):
        r = cliente.get("/api/libros", params={"q": "Clean"})
        assert [l["titulo"] for l in r.json()] == ["Clean Code"]

    def test_busqueda_por_autor(self, cliente):
        r = cliente.get("/api/libros", params={"q": "Bosch"})
        assert r.json()[0]["autor"] == "Juan Bosch"

    def test_la_busqueda_no_distingue_mayusculas(self, cliente):
        assert cliente.get("/api/libros", params={"q": "clean"}).json()

    def test_busqueda_sin_resultados_devuelve_lista_vacia(self, cliente):
        r = cliente.get("/api/libros", params={"q": "zzzznoexiste"})
        assert r.status_code == 200 and r.json() == []

    def test_filtrado_por_categoria(self, cliente):
        r = cliente.get("/api/libros", params={"categoria": "Literatura"})
        assert all(l["categoria"] == "Literatura" for l in r.json())
        assert len(r.json()) == 2


class TestCrearLibro:
    """RF-02 / HU-02: registrar un titulo nuevo."""

    def test_crea_y_devuelve_201(self, cliente):
        r = cliente.post("/api/libros", json=LIBRO_NUEVO)
        assert r.status_code == 201
        assert r.json()["titulo"] == "Refactoring"
        assert r.json()["disponibles"] == 2

    def test_el_libro_creado_aparece_en_el_listado(self, cliente):
        cliente.post("/api/libros", json=LIBRO_NUEVO)
        assert len(cliente.get("/api/libros").json()) == 11

    def test_rechaza_isbn_duplicado(self, cliente):
        cliente.post("/api/libros", json=LIBRO_NUEVO)
        r = cliente.post("/api/libros", json=LIBRO_NUEVO)
        assert r.status_code == 409
        assert "ya existe" in r.json()["detail"].lower()

    def test_rechaza_titulo_vacio(self, cliente):
        r = cliente.post("/api/libros", json=LIBRO_NUEVO | {"titulo": "   "})
        assert r.status_code == 422

    def test_rechaza_cero_ejemplares(self, cliente):
        r = cliente.post("/api/libros", json=LIBRO_NUEVO | {"ejemplares": 0})
        assert r.status_code == 422

    def test_rechaza_isbn_demasiado_corto(self, cliente):
        r = cliente.post("/api/libros", json=LIBRO_NUEVO | {"isbn": "123"})
        assert r.status_code == 422

    def test_recorta_los_espacios_sobrantes(self, cliente):
        r = cliente.post("/api/libros",
                         json=LIBRO_NUEVO | {"titulo": "  Refactoring  "})
        assert r.json()["titulo"] == "Refactoring"


class TestActualizarYEliminar:
    """RF-02 / RF-03."""

    def test_actualiza_un_campo(self, cliente):
        r = cliente.put("/api/libros/1", json={"categoria": "Clasicos"})
        assert r.status_code == 200 and r.json()["categoria"] == "Clasicos"

    def test_actualizar_un_libro_inexistente_da_404(self, cliente):
        r = cliente.put("/api/libros/9999", json={"categoria": "X"})
        assert r.status_code == 404

    def test_actualizar_sin_campos_da_400(self, cliente):
        assert cliente.put("/api/libros/1", json={}).status_code == 400

    def test_elimina_un_libro_sin_prestamos(self, cliente):
        assert cliente.delete("/api/libros/1").status_code == 204
        assert cliente.get("/api/libros/1").status_code == 404

    def test_no_permite_eliminar_un_libro_prestado(self, cliente):
        cliente.post("/api/prestamos", json={"socio_id": 1, "libro_id": 1})
        r = cliente.delete("/api/libros/1")
        assert r.status_code == 409
        assert "prestados" in r.json()["detail"]

    def test_no_permite_dejar_el_inventario_bajo_lo_prestado(self, cliente):
        cliente.post("/api/prestamos", json={"socio_id": 1, "libro_id": 1})
        r = cliente.put("/api/libros/1", json={"ejemplares": 0})
        assert r.status_code == 409


class TestSocios:
    """RF-08 / HU-09: gestion de socios."""

    NUEVO = {"matricula": "20239999", "nombre": "Pedro Antonio Luna",
             "correo": "pedro.luna@itla.edu.do", "telefono": "809-555-9999"}

    def test_lista_los_socios_iniciales(self, cliente):
        assert len(cliente.get("/api/socios").json()) == 5

    def test_crea_un_socio(self, cliente):
        r = cliente.post("/api/socios", json=self.NUEVO)
        assert r.status_code == 201 and r.json()["activo"] is True

    def test_rechaza_matricula_duplicada(self, cliente):
        cliente.post("/api/socios", json=self.NUEVO)
        assert cliente.post("/api/socios", json=self.NUEVO).status_code == 409

    def test_rechaza_correo_invalido(self, cliente):
        r = cliente.post("/api/socios", json=self.NUEVO | {"correo": "no-es-correo"})
        assert r.status_code == 422

    def test_busca_por_matricula(self, cliente):
        r = cliente.get("/api/socios", params={"q": "20231395"})
        assert r.json()[0]["nombre"].startswith("Triana")

    def test_desactiva_un_socio(self, cliente):
        r = cliente.put("/api/socios/1", json={"activo": False})
        assert r.status_code == 200 and r.json()["activo"] is False


class TestAutenticacion:
    """RF-09 / HU-10."""

    def test_credenciales_correctas(self, cliente):
        r = cliente.post("/api/login", json={"nombre_usuario": "admin",
                                             "clave": "BiblioITLA2026"})
        assert r.status_code == 200 and r.json()["rol"] == "administrador"

    def test_clave_incorrecta_da_401(self, cliente):
        r = cliente.post("/api/login", json={"nombre_usuario": "admin",
                                             "clave": "incorrecta"})
        assert r.status_code == 401

    def test_usuario_inexistente_da_401(self, cliente):
        r = cliente.post("/api/login", json={"nombre_usuario": "nadie",
                                             "clave": "x"})
        assert r.status_code == 401
