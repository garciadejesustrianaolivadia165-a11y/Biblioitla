"""
Pruebas de extremo a extremo con navegador real (Chromium + Playwright).

Recorren la aplicacion como lo haria el bibliotecario: iniciar sesion,
registrar un libro, prestarlo, intentar prestarlo otra vez y devolverlo.
Cada prueba deja una captura en evidencias/capturas y un video en
evidencias/videos.

Trazabilidad: HU-01 a HU-10 (flujos del primer Release)
"""

import pytest

pytestmark = pytest.mark.e2e


class TestAcceso:
    """HU-10: control de acceso."""

    def test_sin_sesion_redirige_al_login(self, pagina):
        pagina.goto(f"{pagina.base_url}/")
        assert pagina.url.endswith("/login")

    def test_credenciales_invalidas_muestran_error(self, pagina):
        pagina.goto(f"{pagina.base_url}/login")
        pagina.fill('[data-test="usuario"]', "admin")
        pagina.fill('[data-test="clave"]', "clave-mala")
        pagina.click('[data-test="entrar"]')
        assert pagina.is_visible('[data-test="error-login"]')

    def test_login_correcto_lleva_al_panel(self, pagina):
        pagina.goto(f"{pagina.base_url}/login")
        pagina.fill('[data-test="usuario"]', "admin")
        pagina.fill('[data-test="clave"]', "BiblioITLA2026")
        pagina.click('[data-test="entrar"]')
        pagina.wait_for_url(f"{pagina.base_url}/")
        assert "Panel de control" in pagina.inner_text("h1")

    def test_cerrar_sesion(self, sesion_iniciada):
        pagina = sesion_iniciada
        pagina.click("text=Salir")
        pagina.wait_for_url("**/login")
        pagina.goto(f"{pagina.base_url}/libros")
        assert pagina.url.endswith("/login")


class TestPanel:
    """HU-08: indicadores del panel."""

    def test_muestra_los_indicadores(self, sesion_iniciada):
        pagina = sesion_iniciada
        assert pagina.inner_text('[data-test="titulos"]') == "10"
        assert int(pagina.inner_text('[data-test="ejemplares"]')) > 0
        assert pagina.inner_text('[data-test="activos"]') == "0"


class TestCatalogo:
    """HU-01, HU-02, HU-03."""

    def test_lista_el_catalogo(self, sesion_iniciada):
        pagina = sesion_iniciada
        pagina.click("text=Libros")
        pagina.wait_for_url("**/libros")
        assert pagina.locator('[data-test="fila-libro"]').count() == 10

    def test_registrar_un_libro(self, sesion_iniciada):
        pagina = sesion_iniciada
        pagina.goto(f"{pagina.base_url}/libros")
        pagina.fill('[data-test="isbn"]', "978-0596517748")
        pagina.fill('[data-test="titulo"]', "JavaScript: The Good Parts")
        pagina.fill('[data-test="autor"]', "Douglas Crockford")
        pagina.fill('[data-test="categoria"]', "Programacion")
        pagina.fill('[data-test="ejemplares"]', "2")
        pagina.click('[data-test="guardar-libro"]')
        pagina.wait_for_url("**/libros?mensaje=*")

        assert pagina.is_visible('[data-test="mensaje"]')
        assert pagina.locator('[data-test="fila-libro"]').count() == 11
        assert "JavaScript" in pagina.inner_text('[data-test="tabla-libros"]')

    def test_isbn_duplicado_muestra_error(self, sesion_iniciada):
        pagina = sesion_iniciada
        pagina.goto(f"{pagina.base_url}/libros")
        pagina.fill('[data-test="isbn"]', "978-0132350884")   # ya existe
        pagina.fill('[data-test="titulo"]', "Copia de Clean Code")
        pagina.fill('[data-test="autor"]', "Robert C. Martin")
        pagina.click('[data-test="guardar-libro"]')
        pagina.wait_for_url("**/libros?error=*")
        assert "Ya existe" in pagina.inner_text('[data-test="error"]')

    def test_buscar_por_titulo(self, sesion_iniciada):
        pagina = sesion_iniciada
        pagina.goto(f"{pagina.base_url}/libros")
        pagina.fill('[data-test="buscar"]', "Bosch")
        pagina.click('[data-test="btn-buscar"]')
        pagina.wait_for_url("**/libros?q=Bosch*")
        assert pagina.locator('[data-test="fila-libro"]').count() == 1
        assert "Mananosa" in pagina.inner_text('[data-test="tabla-libros"]')


class TestSocios:
    """HU-09."""

    def test_registrar_un_socio(self, sesion_iniciada):
        pagina = sesion_iniciada
        pagina.goto(f"{pagina.base_url}/socios")
        antes = pagina.locator('[data-test="fila-socio"]').count()
        pagina.fill('[data-test="matricula"]', "20240777")
        pagina.fill('[data-test="nombre-socio"]', "Carlos Alberto Nunez")
        pagina.fill('[data-test="correo"]', "20240777@itla.edu.do")
        pagina.click('[data-test="guardar-socio"]')
        pagina.wait_for_url("**/socios?mensaje=*")
        assert pagina.locator('[data-test="fila-socio"]').count() == antes + 1


class TestCircuitoDePrestamo:
    """HU-04 a HU-07: el flujo completo del negocio."""

    def _prestar(self, pagina, indice_socio=1, indice_libro=1):
        pagina.goto(f"{pagina.base_url}/prestamos")
        pagina.select_option('[data-test="sel-socio"]', index=indice_socio)
        pagina.select_option('[data-test="sel-libro"]', index=indice_libro)
        pagina.click('[data-test="guardar-prestamo"]')

    def test_prestar_y_devolver(self, sesion_iniciada):
        pagina = sesion_iniciada

        # --- prestar ---
        self._prestar(pagina)
        pagina.wait_for_url("**/prestamos?mensaje=*")
        assert pagina.is_visible('[data-test="mensaje"]')
        assert pagina.locator('[data-test="fila-prestamo"]').count() == 1

        # el panel refleja el prestamo
        pagina.goto(f"{pagina.base_url}/")
        assert pagina.inner_text('[data-test="activos"]') == "1"

        # --- devolver ---
        pagina.goto(f"{pagina.base_url}/prestamos")
        pagina.click('[data-test="devolver"]')
        pagina.wait_for_url("**/prestamos?mensaje=*")
        assert pagina.locator('[data-test="fila-prestamo"]').count() == 0

        pagina.goto(f"{pagina.base_url}/prestamos?estado=devueltos")
        assert pagina.locator('[data-test="fila-prestamo"]').count() == 1

        pagina.goto(f"{pagina.base_url}/")
        assert pagina.inner_text('[data-test="activos"]') == "0"

    def test_no_permite_prestar_el_mismo_libro_al_mismo_socio(self, sesion_iniciada):
        pagina = sesion_iniciada
        self._prestar(pagina)
        pagina.wait_for_url("**/prestamos?*")
        self._prestar(pagina)
        pagina.wait_for_url("**/prestamos?error=*")
        assert "sin devolver" in pagina.inner_text('[data-test="error"]')

    def test_respeta_el_limite_de_tres_prestamos(self, sesion_iniciada):
        pagina = sesion_iniciada
        for indice in (1, 2, 3):
            self._prestar(pagina, indice_libro=indice)
            pagina.wait_for_url("**/prestamos?*")
        self._prestar(pagina, indice_libro=4)
        pagina.wait_for_url("**/prestamos?error=*")
        assert "maximo" in pagina.inner_text('[data-test="error"]')
