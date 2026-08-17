# BiblioITLA — Sistema de Gestión de Biblioteca

Proyecto Final de **Programación III** · Instituto Tecnológico de las Américas
(ITLA) · Triana Olivadia García de Jesús

Aplicación web para administrar el catálogo, los socios y el circuito de
préstamos de una biblioteca, desarrollada con metodología **Agile-Scrum** y
con una batería de **99 pruebas automatizadas** en tres niveles.

---

## Estado de las pruebas

| Nivel | Pruebas | Qué comprueba |
|---|---|---|
| Unitarias | 30 | Reglas de negocio puras (plazos, mora, límites) |
| API / integración | 56 | HTTP → validación → servicios → base de datos |
| E2E (navegador) | 13 | Flujos completos en Chromium con Playwright |
| **Total** | **99** | Cobertura del código de aplicación: **83 %** |

```bash
PYTHONPATH=. pytest                       # las 99
PYTHONPATH=. pytest pruebas/unitarias     # solo unitarias (rápidas)
PYTHONPATH=. pytest pruebas/e2e -v        # solo navegador
PYTHONPATH=. pytest --cov=app --cov-report=html:evidencias/cobertura
PYTHONPATH=. pytest -k "mora"             # una prueba concreta por nombre
```

## Puesta en marcha

```bash
pip install -r requirements.txt
python -m playwright install chromium     # solo para las pruebas E2E
PYTHONPATH=. uvicorn app.principal:aplicacion --reload
```

Abrir <http://localhost:8000> · usuario `admin` · contraseña `BiblioITLA2026`.

La base de datos SQLite se crea sola en el primer arranque, con un catálogo de
10 libros y 5 socios de ejemplo.

## Qué hace el sistema (Release 1)

| Historia | Funcionalidad |
|---|---|
| HU-01 | Consultar el catálogo con disponibilidad en tiempo real |
| HU-02 | Registrar libros (ISBN único, validaciones) |
| HU-03 | Buscar por título, autor o ISBN y filtrar por categoría |
| HU-04 | Registrar préstamos aplicando las cuatro reglas del negocio |
| HU-05 | Registrar devoluciones y reponer el inventario |
| HU-06 | Calcular automáticamente la mora por retraso |
| HU-07 | Consultar préstamos por estado (activos, vencidos, devueltos) |
| HU-08 | Panel con indicadores y libros más prestados |
| HU-09 | Registrar y consultar socios |
| HU-10 | Inicio de sesión y control de acceso |

### Reglas de negocio

1. El préstamo dura **14 días**.
2. Un socio puede tener como máximo **3 préstamos activos**.
3. No se presta un título del que **no queden ejemplares**.
4. Un socio **no puede repetir** un título que aún no ha devuelto.
5. Un **socio inactivo** no puede tomar prestado.
6. Retraso: **RD$ 25 por día**; devolver a tiempo no genera cargo.
7. No se elimina un libro con ejemplares prestados, ni se deja el inventario
   por debajo de lo que está fuera.

## Arquitectura

```
app/modelos.py       Entidades SQLAlchemy (Usuario, Socio, Libro, Prestamo)
app/reglas.py        Reglas de negocio como funciones puras  ← núcleo probado
app/servicios.py     Consulta datos, aplica reglas y persiste
app/routers/api.py   API REST (/api/...)
app/routers/web.py   Interfaz web con Jinja2
app/base_datos.py    Motor, sesiones, cifrado de claves y datos iniciales
```

La decisión de diseño central es **aislar las reglas de negocio en funciones
puras**, sin base de datos ni HTTP. Eso permite probarlas exhaustivamente en
milisegundos y deja las capas superiores como simple coordinación. Las 30
pruebas unitarias cubren `reglas.py` al 100 %.

La API devuelve **409 Conflict** cuando se incumple una política de la
biblioteca, para distinguirlo de un error de validación (422) o de un recurso
inexistente (404).

## Documentación y evidencias

| Archivo | Contenido |
|---|---|
| `documentacion/historias_usuario_jira.csv` | Las 10 historias y 4 épicas, listas para importar en Jira |
| `evidencias/demo/demo_biblioitla.mp4` | Video del recorrido por el Release 1 |
| `evidencias/capturas/` | Captura de cada prueba E2E |
| `evidencias/cobertura/index.html` | Informe de cobertura navegable |
| `.github/workflows/pruebas.yml` | Integración continua con las tres capas |

Para regenerar el video de demostración:

```bash
PYTHONPATH=. python herramientas/grabar_demo.py
```

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/libros?q=&categoria=` | Listar y buscar libros |
| POST | `/api/libros` | Registrar un libro |
| PUT/DELETE | `/api/libros/{id}` | Actualizar / eliminar |
| GET/POST | `/api/socios` | Listar y registrar socios |
| GET/POST | `/api/prestamos` | Consultar y registrar préstamos |
| POST | `/api/prestamos/{id}/devolucion` | Registrar la devolución |
| GET | `/api/reportes/resumen` | Indicadores del panel |
| GET | `/api/salud` | Estado del servicio |

Documentación interactiva generada automáticamente en `/docs`.

## Tecnología

Python 3.11 · FastAPI · SQLAlchemy 2.0 · SQLite · Jinja2 · Pydantic ·
pytest · Playwright · GitHub Actions.
