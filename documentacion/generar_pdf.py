"""
Genera el PDF del Proyecto Final a partir de los mismos datos que el .docx
(contenido.py), renderizando HTML con Chromium.

NOTA SOBRE LA FUENTE: el .docx usa Calibri de verdad. Este equipo no tiene esa
fuente instalada ni su clon metrico (Carlito), asi que el PDF generado aqui cae
en Liberation Sans. Para obtener el PDF exactamente en Calibri, abrir el .docx
en Word y exportarlo con «Guardar como PDF».

Uso:  python3 documentacion/generar_pdf.py
"""

import html
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import contenido as C  # noqa: E402

SALIDA = AQUI / "Proyecto_Final_Programacion_III_Triana_Garcia.pdf"
TEMPORAL = AQUI / "_documento.html"
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

CSS = """
@page { size: Letter; margin: 2.5cm 2.5cm 2.2cm 2.5cm; }
body { font-family: Calibri, Carlito, "Liberation Sans", sans-serif;
       font-size: 11pt; line-height: 1.15; color: #111; margin: 0; }
p { text-align: justify; margin: 0 0 6pt; }
h1 { font-family: "Calibri Light", Calibri, "Liberation Sans", sans-serif;
     font-size: 16pt; color: #1F3A64; margin: 18pt 0 8pt;
     page-break-after: avoid; }
h2 { font-family: "Calibri Light", Calibri, "Liberation Sans", sans-serif;
     font-size: 14pt; color: #1F3A64; margin: 14pt 0 6pt;
     page-break-after: avoid; }
h3 { font-family: "Calibri Light", Calibri, "Liberation Sans", sans-serif;
     font-size: 12pt; color: #595959; margin: 12pt 0 5pt;
     page-break-after: avoid; }
ul, ol { margin: 0 0 8pt 18pt; padding: 0; }
li { text-align: justify; margin-bottom: 3pt; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 10pt;
        font-size: 9pt; page-break-inside: avoid; }
th { background: #1F3A64; color: #fff; text-align: left; padding: 4pt 5pt;
     border: 0.5pt solid #1F3A64; font-weight: bold; }
td { border: 0.5pt solid #999; padding: 4pt 5pt; vertical-align: top; }
.leyenda { font-size: 9pt; font-style: italic; color: #595959;
           margin: 8pt 0 2pt; }
.salto { page-break-after: always; }
.portada { text-align: center; padding-top: 3cm; }
.portada .inst { font-size: 14pt; font-weight: bold; }
.portada .carrera { font-size: 12pt; margin-bottom: 3cm; }
.portada .tipo { font-size: 20pt; font-weight: bold; color: #1F3A64;
                 margin-bottom: 4pt; }
.portada .asig { font-size: 14pt; margin-bottom: 3cm; }
.portada .titulo { font-size: 16pt; font-weight: bold; color: #1F3A64; }
.portada .sub { font-style: italic; margin-bottom: 4cm; }
.portada .dato { margin-bottom: 4pt; }
.portada .lugar { font-size: 10pt; color: #595959; margin-top: 1.5cm; }
.indice .n0 { font-weight: bold; margin: 3pt 0; }
.indice .n1 { margin: 2pt 0 2pt 24pt; }
.nota { font-size: 10pt; font-style: italic; color: #444; }
.hu-narrativa { font-style: italic; margin-bottom: 5pt; }
"""


def e(t):
    return html.escape(str(t))


def tabla(encabezados, filas, leyenda=None, anchos=None):
    out = []
    if leyenda:
        out.append(f'<p class="leyenda">{e(leyenda)}</p>')
    cols = ""
    if anchos:
        total = sum(anchos)
        cols = "<colgroup>" + "".join(
            f'<col style="width:{a / total * 100:.1f}%">' for a in anchos) + "</colgroup>"
    out.append("<table>" + cols + "<thead><tr>"
               + "".join(f"<th>{e(h)}</th>" for h in encabezados)
               + "</tr></thead><tbody>")
    for fila in filas:
        celdas = "".join(
            f"<td>{e(c).replace(chr(10), '<br>')}</td>" for c in fila)
        out.append(f"<tr>{celdas}</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def lista(elementos, ordenada=False):
    etq = "ol" if ordenada else "ul"
    return (f"<{etq}>" + "".join(f"<li>{e(x)}</li>" for x in elementos)
            + f"</{etq}>")


def construir():
    h = []
    a = h.append

    # ------------------------------------------------------------- portada
    a('<div class="portada">')
    a(f'<div class="inst">{e(C.INSTITUCION)}</div>')
    a('<div class="carrera">Tecnólogo en Desarrollo de Software</div>')
    a('<div class="tipo">PROYECTO FINAL</div>')
    a(f'<div class="asig">{e(C.ASIGNATURA)}</div>')
    a(f'<div class="titulo">{e(C.PROYECTO)}</div>')
    a('<div class="sub">Aplicación web desarrollada con metodología Agile-Scrum</div>')
    for etiqueta, valor in [("Sustentante", C.AUTOR), ("Matrícula", C.MATRICULA),
                            ("Asignatura", C.ASIGNATURA), ("Facilitador", C.PROFESOR),
                            ("Fecha de entrega", C.FECHA)]:
        a(f'<div class="dato"><b>{e(etiqueta)}:</b> {e(valor)}</div>')
    a('<div class="lugar">Santo Domingo, República Dominicana</div>')
    a('</div><div class="salto"></div>')

    # -------------------------------------------------------------- indice
    from generar_documento import INDICE
    a("<h1>Índice</h1><div class='indice'>")
    for numero, titulo, nivel in INDICE:
        a(f'<div class="n{nivel}">{e(numero)} {e(titulo)}</div>')
    a("</div><div class='salto'></div>")

    # -------------------------------------------------------- introduccion
    a("<h1>1. Introducción</h1>")
    for p in [
        "Este documento recoge el desarrollo completo de BiblioITLA, un sistema "
        "de gestión de biblioteca construido como Proyecto Final de la "
        "asignatura Programación III. El trabajo no se limita a programar una "
        "aplicación: documenta cómo se planificó, cómo se organizó con Scrum, "
        "cómo se probó y qué resultados arrojaron esas pruebas.",
        "El problema de partida es concreto. Una biblioteca académica que "
        "controla sus préstamos en hojas de cálculo depende de que el personal "
        "recuerde las políticas: cuántos libros puede llevarse cada socio, "
        "cuándo vence un préstamo y cuánta mora corresponde cobrar. Ese control "
        "manual falla precisamente cuando hay más movimiento. La propuesta "
        "consiste en trasladar esas reglas al software, de modo que un préstamo "
        "que incumple una política sea sencillamente imposible de registrar.",
        "El proyecto se organizó en tres sprints de dos semanas siguiendo el "
        "marco Scrum, con diez historias de usuario repartidas en cuatro "
        "épicas. El primer Release cubre el circuito completo del negocio, "
        "desde el inicio de sesión hasta el cobro de la mora.",
        "El apartado de mayor peso es el plan de pruebas. Se construyó una "
        "batería de 99 pruebas automatizadas en tres niveles —unitarias, de "
        "integración y de extremo a extremo con navegador real— que se ejecutan "
        "automáticamente ante cada cambio del código. Ese trabajo no es "
        "decorativo: detectó dos defectos reales antes de la entrega, "
        "documentados en el apartado 4.8.",
        "El documento sigue el orden en que se hizo el trabajo: primero la "
        "planificación, luego la organización con Scrum, después el plan de "
        "pruebas con sus resultados y finalmente las conclusiones sobre lo que "
        "funcionó y lo que quedó pendiente.",
    ]:
        a(f"<p>{e(p)}</p>")
    a("<div class='salto'></div>")

    # ---------------------------------------------------------- estrategia
    a("<h1>2. Estrategia de trabajo (planificación)</h1>")
    a("<h2>2.1. Nombre del proyecto de software</h2>")
    a(f"<p><b>{e(C.PROYECTO)}</b></p>")
    a("<p>El nombre combina la actividad del sistema (biblioteca) con la "
      "institución para la que se plantea (ITLA). Es corto, se pronuncia con "
      "facilidad y describe sin ambigüedad de qué trata el producto.</p>")

    a("<h2>2.2. Tecnología a aplicar</h2>")
    a("<p>La selección buscó herramientas maduras, con buena documentación y "
      "que permitieran automatizar las pruebas sin infraestructura adicional. "
      "La última columna explica por qué se eligió cada una.</p>")
    a(tabla(["Componente", "Tecnología", "Justificación"], C.TECNOLOGIA,
            "Tabla 1. Tecnologías seleccionadas y justificación.", [3, 3, 9]))

    a("<h2>2.3. Objetivo del proyecto</h2>")
    a("<p><b>Objetivo general</b></p>")
    a(f"<p>{e(C.OBJETIVO)}</p>")
    a("<p><b>Objetivos específicos</b></p>")
    a(lista(C.OBJETIVOS_ESPECIFICOS))

    a("<h2>2.4. Alcance del proyecto</h2>")
    a("<p>Delimitar lo que el sistema no hace es tan importante como describir "
      "lo que hace: evita expectativas equivocadas y protege el alcance del "
      "Release durante el desarrollo.</p>")
    a("<p><b>El sistema incluye:</b></p>")
    a(lista(C.ALCANCE_INCLUYE))
    a("<p><b>El sistema NO incluye en este Release:</b></p>")
    a(lista(C.ALCANCE_EXCLUYE))

    a("<h2>2.5. Cronograma del proyecto</h2>")
    a(tabla(["#", "Actividad", "Inicio", "Fin", "Duración", "Responsable"],
            C.CRONOGRAMA,
            "Tabla 2. Cronograma de actividades, plazos y responsables.",
            [0.8, 6, 2, 2, 1.6, 2.6]))

    a("<h2>2.6. Definición del primer Release</h2>")
    a(f"<p>{e(C.RELEASE_DESCRIPCION)}</p>")
    a("<p>El Release 1 se compone de las diez historias de usuario del apartado "
      "3.6, que suman 45 puntos de historia repartidos en tres sprints de dos "
      "semanas. Todas ellas están implementadas, probadas y demostradas en el "
      "video de entrega.</p>")

    a("<h2>2.7. Requerimientos funcionales y no funcionales</h2>")
    a("<p><b>Requerimientos funcionales</b></p>")
    a(tabla(["ID", "Nombre", "Descripción", "Historia", "Prioridad"],
            C.REQUISITOS_FUNCIONALES,
            "Tabla 3. Requerimientos funcionales del Release 1.",
            [1.1, 3, 7.5, 1.7, 1.3]))
    a("<p><b>Requerimientos no funcionales</b></p>")
    a(tabla(["ID", "Categoría", "Descripción", "Cómo se verifica"],
            C.REQUISITOS_NO_FUNCIONALES,
            "Tabla 4. Requerimientos no funcionales y forma de verificarlos.",
            [1.1, 2.4, 6.2, 5]))
    a("<div class='salto'></div>")

    # --------------------------------------------------------------- scrum
    a("<h1>3. Metodología Scrum</h1>")
    a("<p>El proyecto se organizó con Scrum en tres sprints de dos semanas. Se "
      "eligió este marco porque el circuito de préstamos se comprendió mejor al "
      "construirlo: trabajar por incrementos permitió incorporar reglas que no "
      "estaban en el planteamiento inicial sin rehacer el trabajo ya hecho.</p>")

    a("<h2>3.1. Tareas a ejecutar</h2>")
    a("<p>Las historias de usuario se descompusieron en veinte tareas técnicas. "
      "Una tarea es trabajo concreto para una persona, con una estimación en "
      "horas, mientras que una historia expresa valor para el usuario.</p>")
    a(tabla(["ID", "Tarea", "Rol responsable", "Sprint", "Estimación"], C.TAREAS,
            "Tabla 5. Descomposición del trabajo en tareas técnicas.",
            [1.1, 7, 2.8, 1.8, 1.8]))

    a("<h2>3.2. Equipo de trabajo</h2>")
    a(tabla(["Rol", "Integrante", "Habilidades requeridas", "Responsabilidades"],
            C.EQUIPO, "Tabla 6. Roles, habilidades y responsabilidades.",
            [2.6, 2.4, 4.8, 5]))
    a(f'<p class="nota">{e(C.NOTA_EQUIPO)}</p>')

    a("<h2>3.3. Herramientas de gestión</h2>")
    a("<p>El seguimiento del trabajo se llevó en Jira Software, en un proyecto "
      "de tipo Scrum con su tablero, su Product Backlog y un Sprint Backlog por "
      "iteración. Las diez historias y las cuatro épicas están cargadas allí con "
      "sus criterios de aceptación y sus puntos de historia.</p>")
    a("<p>Se eligió Jira por ser el estándar en la industria y por distinguir de "
      "forma nativa entre épicas, historias y tareas, algo que un tablero "
      "genérico de tarjetas no hace. El repositorio incluye además el archivo "
      "historias_usuario_jira.csv, que permite reconstruir el tablero completo "
      "mediante la importación de datos de Jira.</p>")
    a(tabla(["Herramienta", "Uso en el proyecto"],
            [["Jira Software", "Product Backlog, Sprint Backlog, tablero y seguimiento de las historias."],
             ["GitHub", "Alojamiento del repositorio e historial de cambios."],
             ["GitHub Actions", "Integración continua: ejecuta las 99 pruebas ante cada cambio."],
             ["Visual Studio Code", "Entorno de desarrollo."],
             ["Microsoft Teams", "Ceremonias de Scrum y comunicación."],
             ["OneDrive institucional", "Entrega del documento y del video."]],
            "Tabla 7. Herramientas de soporte al proyecto.", [4, 11]))

    a("<h2>3.4. Épicas</h2>")
    a("<p>Las historias se agruparon en cuatro épicas según el área funcional "
      "que abordan. La épica del circuito de préstamos es la más grande porque "
      "concentra las reglas de negocio del sistema.</p>")
    a(tabla(["ID", "Épica", "Descripción", "Historias", "Puntos"], C.EPICAS,
            "Tabla 8. Épicas del Release 1.", [1.1, 3, 6.2, 2.7, 1.2]))

    a("<h2>3.5. Ceremonias de Scrum</h2>")
    a("<p>Las ceremonias se planificaron con fecha y hora fijas para los tres "
      "sprints: Sprint 1 del 22 de junio al 3 de julio, Sprint 2 del 6 al 17 de "
      "julio y Sprint 3 del 20 al 31 de julio de 2026.</p>")
    a(tabla(["Ceremonia", "Cuándo", "Duración", "Horario", "Participantes",
             "Propósito"], C.CEREMONIAS, "Tabla 9. Calendario de ceremonias.",
            [2.2, 3.6, 1.4, 1.7, 2.1, 3.2]))

    a("<h2>3.6. Historias de usuario</h2>")
    a("<p>Las diez historias siguen el formato «Como… quiero… para…», que obliga "
      "a expresar quién necesita la función y para qué, no solo qué hace el "
      "sistema. Cada una lleva sus criterios de aceptación y su estimación en "
      "puntos de historia según la sucesión de Fibonacci (3, 5, 8), donde el "
      "valor refleja la complejidad y no las horas de trabajo.</p>")
    a("<p>HU-04 es la historia de mayor puntuación (8) porque concentra las "
      "cuatro validaciones del negocio; HU-01, HU-03, HU-07 y HU-10 son las más "
      "sencillas (3). El total asciende a 45 puntos.</p>")
    for hid, titulo, narrativa, criterios, puntos, epica, sprint, prioridad in C.HISTORIAS:
        a(f"<h3>{e(hid)} — {e(titulo)}</h3>")
        a(f'<p class="hu-narrativa">{e(narrativa)}</p>')
        a(tabla(["Épica", "Sprint", "Prioridad", "Puntos de historia"],
                [[epica, sprint, prioridad, puntos]], None, [1, 1, 1, 1]))
        a("<p><b>Criterios de aceptación:</b></p>")
        a(lista(criterios, ordenada=True))

    resumen = [[h[0], h[1], h[5], h[6], h[4]] for h in C.HISTORIAS]
    resumen.append(["", "TOTAL", "", "", sum(h[4] for h in C.HISTORIAS)])
    a(tabla(["ID", "Historia", "Épica", "Sprint", "Puntos"], resumen,
            "Tabla 10. Resumen de historias y distribución por sprint.",
            [1.2, 6.2, 2.2, 2.2, 1.3]))
    a("<div class='salto'></div>")

    # -------------------------------------------------------- plan pruebas
    a("<h1>4. Plan de pruebas</h1>")
    a("<p>Este plan define qué se prueba, cómo se decide si el resultado es "
      "aceptable, con qué herramientas, quién lo ejecuta y cuándo. Su objetivo "
      "no es demostrar que el sistema funciona, sino intentar que falle antes de "
      "que lo haga en producción.</p>")

    a("<h2>4.1. Requerimientos y matriz de trazabilidad</h2>")
    a("<p>Los requerimientos funcionales y no funcionales se listaron en el "
      "apartado 2.7. La matriz siguiente los relaciona con la historia que los "
      "origina y con las pruebas que los verifican, de modo que ningún "
      "requerimiento quede sin comprobar.</p>")
    matriz = [
        ["RF-01", "HU-01", "test_devuelve_el_catalogo_inicial, test_lista_el_catalogo", "API + E2E"],
        ["RF-02", "HU-02", "TestCrearLibro (7 casos), test_registrar_un_libro", "API + E2E"],
        ["RF-03", "HU-03", "TestListarLibros (5 casos), test_buscar_por_titulo", "API + E2E"],
        ["RF-04", "HU-04", "TestCalcularVencimiento (7 casos)", "Unitaria"],
        ["RF-05", "HU-04", "TestValidarPrestamo (8), TestRegistrarPrestamo (11)", "Unitaria + API + E2E"],
        ["RF-06", "HU-05, HU-06", "TestCalcularMora (7), TestDevolucion (6), TestMoraPorRetraso", "Unitaria + API"],
        ["RF-07", "HU-07", "TestConsultarPrestamos (3 casos)", "API"],
        ["RF-08", "HU-09", "TestSocios (6), test_registrar_un_socio", "API + E2E"],
        ["RF-09", "HU-10", "TestAutenticacion (3), TestAcceso (4)", "API + E2E"],
        ["RF-10", "HU-08", "TestReportes (4), test_muestra_los_indicadores", "API + E2E"],
    ]
    a(tabla(["Requerimiento", "Historia", "Pruebas que lo verifican", "Nivel"],
            matriz,
            "Tabla 11. Matriz de trazabilidad requerimiento – historia – prueba.",
            [2.2, 2.2, 7, 3.2]))

    a("<h2>4.2. Criterios de aceptación y de rechazo</h2>")
    for titulo, elementos in [
            ("Criterios de entrada (cuándo se puede empezar a probar)", C.CRITERIOS_ENTRADA),
            ("Criterios de aceptación (cuándo se aprueba el Release)", C.CRITERIOS_ACEPTACION),
            ("Criterios de rechazo (cuándo se devuelve a desarrollo)", C.CRITERIOS_RECHAZO),
            ("Criterios de suspensión (cuándo se detienen las pruebas)", C.CRITERIOS_SUSPENSION)]:
        a(f"<p><b>{e(titulo)}</b></p>")
        a(lista(elementos))

    a("<h2>4.3. Herramientas de pruebas y su justificación</h2>")
    a(tabla(["Herramienta", "Se usa para", "Justificación de la elección"],
            C.HERRAMIENTAS_PRUEBAS,
            "Tabla 12. Herramientas de pruebas y motivo de su elección.",
            [3, 2.8, 9]))

    a("<h2>4.4. Cronograma de ejecución de pruebas</h2>")
    a(tabla(["Actividad", "Inicio", "Fin", "Tipo", "Responsable"],
            C.CRONOGRAMA_PRUEBAS,
            "Tabla 13. Cronograma de pruebas manuales y automatizadas.",
            [6, 2, 2, 2.2, 2.8]))

    a("<h2>4.5. Plantilla de casos de prueba</h2>")
    a("<p>Se adoptó la plantilla siguiente, basada en la norma IEEE 829, para "
      "documentar cada caso de forma uniforme. Los campos son los mínimos que "
      "permiten a otra persona reproducir la prueba sin preguntar nada.</p>")
    a(tabla(["Campo", "Descripción del campo"],
            [["ID del caso", "Identificador único, formato CP-000."],
             ["Historia asociada", "Historia de usuario que origina el caso."],
             ["Título", "Qué se comprueba, en una frase."],
             ["Precondición", "Estado del sistema y datos necesarios antes de empezar."],
             ["Pasos", "Acciones numeradas, en el orden exacto de ejecución."],
             ["Resultado esperado", "Qué debe ocurrir, en términos observables."],
             ["Tipo", "Unitaria, API, E2E; manual o automatizada."],
             ["Resultado obtenido", "Superado o fallido, con la fecha de ejecución."]],
            "Tabla 14. Plantilla estándar para documentar un caso de prueba.",
            [4, 11]))
    a("<p>A continuación se documentan ocho casos representativos con la "
      "plantilla ya rellena. Se eligieron los que cubren las reglas de negocio "
      "más delicadas y los casos negativos, que son los que realmente ponen a "
      "prueba el sistema.</p>")
    for cid, hu, titulo, precondicion, pasos, esperado, tipo, resultado in C.CASOS_PRUEBA:
        pasos_txt = "\n".join(f"{i}. {p}" for i, p in enumerate(pasos, 1))
        a(tabla(["Campo", "Contenido"],
                [["ID del caso", cid], ["Historia asociada", hu],
                 ["Título", titulo], ["Precondición", precondicion],
                 ["Pasos", pasos_txt], ["Resultado esperado", esperado],
                 ["Tipo", tipo],
                 ["Resultado obtenido", f"{resultado} (15/08/2026)"]],
                f"{cid} — {titulo}", [3.4, 11.6]))

    a("<h2>4.6. Equipo de pruebas y responsabilidades</h2>")
    a(tabla(["Rol", "Responsable", "Responsabilidades en las pruebas"],
            C.EQUIPO_PRUEBAS,
            "Tabla 15. Responsabilidades en el proceso de pruebas.", [3, 2.8, 9]))

    a("<h2>4.7. Plan de automatización de pruebas</h2>")
    a("<p>La automatización se organizó en tres niveles siguiendo la pirámide de "
      "pruebas descrita por Fowler (2012): cuanto más abajo está una prueba, más "
      "rápida y estable es, y más de ellas conviene tener.</p>")
    a(tabla(["Nivel", "Cantidad", "Qué cubre", "Herramienta", "Velocidad",
             "Detalle"], C.PLAN_AUTOMATIZACION,
            "Tabla 16. Niveles de automatización implementados.",
            [2.3, 1.6, 2.9, 2.2, 1.7, 4.3]))
    a("<p><b>Estrategia y decisiones tomadas</b></p>")
    a(lista(C.ESTRATEGIA_AUTOMATIZACION))

    a("<h2>4.8. Ejecución de las pruebas y evidencias</h2>")
    a("<p>La suite completa se ejecutó el 15 de agosto de 2026 sobre el "
      "Release 1. Los resultados son los siguientes.</p>")
    a(tabla(["Nivel", "Total", "Superadas", "Fallidas", "Porcentaje"],
            C.RESULTADOS, "Tabla 17. Resultados de la última ejecución completa.",
            [4.4, 2.4, 2.6, 2.4, 2.8]))
    a("<p><b>Cobertura de código</b></p>")
    a(tabla(["Módulo", "Responsabilidad", "Cobertura"], C.COBERTURA,
            "Tabla 18. Cobertura por módulo.", [5, 6.5, 3.4]))
    a(f'<p class="nota">{e(C.NOTA_COBERTURA)}</p>')
    a("<p><b>Defectos detectados por la automatización</b></p>")
    a("<p>Los dos defectos siguientes fueron encontrados por las pruebas "
      "automatizadas durante el desarrollo, no por un usuario. Se documentan "
      "porque son la evidencia concreta de que el plan de pruebas cumplió su "
      "función.</p>")
    a(tabla(["ID", "Severidad", "Descripción", "Causa raíz", "Corrección",
             "Estado"], C.DEFECTOS,
            "Tabla 19. Defectos detectados, causa y corrección.",
            [1.2, 1.6, 3.7, 3.7, 3, 1.3]))
    a("<p><b>Evidencias disponibles en el repositorio</b></p>")
    a(lista([
        "evidencias/demo/demo_biblioitla.mp4 — video del recorrido completo por "
        "el Release 1, grabado automáticamente con Playwright.",
        "evidencias/capturas/ — una captura de pantalla por cada prueba E2E, "
        "generada automáticamente al finalizar cada caso.",
        "evidencias/videos/ — grabación en video de cada prueba E2E ejecutándose.",
        "evidencias/cobertura/index.html — informe de cobertura navegable, línea "
        "por línea.",
        "Pestaña Actions del repositorio — historial de todas las ejecuciones de "
        "la suite en integración continua.",
    ]))
    a("<div class='salto'></div>")

    # --------------------------------------------------------- entregables
    a("<h1>5. Demostración y entregables</h1>")
    a("<p>El video de demostración recorre el incremento del Release 1 en el "
      "orden en que trabaja el bibliotecario: inicio de sesión, panel de "
      "indicadores, catálogo, alta de un libro, búsqueda, registro de un socio, "
      "préstamo, rechazo de un préstamo que incumple una regla, devolución y "
      "actualización de los indicadores.</p>")
    a("<p>Se incluye a propósito el intento de préstamo rechazado: mostrar solo "
      "el camino correcto no demuestra que las reglas de negocio estén "
      "implementadas.</p>")
    a(tabla(["Entregable", "Enlace"],
            [["Repositorio del código fuente", C.REPOSITORIO],
             ["Tablero de Jira con las historias de usuario", C.TABLERO],
             ["Código de las pruebas automatizadas", f"{C.REPOSITORIO}/tree/main/pruebas"],
             ["Integración continua (ejecuciones de la suite)", f"{C.REPOSITORIO}/actions"],
             ["Video de demostración del Release 1", C.VIDEO]],
            "Tabla 20. Enlaces de la entrega.", [5.4, 9.6]))
    a('<p class="nota">Los enlaces se colocan además en la opción «Texto en '
      'línea» de la plataforma, como exige el reglamento de entrega.</p>')

    # -------------------------------------------------------- conclusiones
    a("<h1>6. Conclusiones</h1>")
    for texto in C.CONCLUSIONES:
        a(f"<p>{e(texto)}</p>")

    # -------------------------------------------------------- bibliografia
    a("<h1>7. Bibliografía</h1>")
    for referencia in C.BIBLIOGRAFIA:
        a(f'<p style="margin-left:1cm;text-indent:-1cm">{e(referencia)}</p>')

    return ("<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            f"<title>Proyecto Final</title><style>{CSS}</style></head><body>"
            + "\n".join(h) + "</body></html>")


def main():
    TEMPORAL.write_text(construir(), encoding="utf-8")
    with sync_playwright() as p:
        opciones = {"args": ["--no-sandbox"]}
        if Path(CHROMIUM).exists():
            opciones["executable_path"] = CHROMIUM
        nav = p.chromium.launch(**opciones)
        pag = nav.new_page()
        pag.goto("file://" + str(TEMPORAL))
        pag.wait_for_timeout(600)
        pag.pdf(path=str(SALIDA), format="Letter", print_background=True,
                margin={"top": "2.5cm", "bottom": "2.2cm",
                        "left": "2.5cm", "right": "2.5cm"},
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=(
                    '<div style="width:100%;font-size:9px;color:#595959;'
                    'text-align:center;font-family:sans-serif">'
                    'Página <span class="pageNumber"></span></div>'))
        nav.close()
    TEMPORAL.unlink(missing_ok=True)
    print(f"PDF generado: {SALIDA} ({SALIDA.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
