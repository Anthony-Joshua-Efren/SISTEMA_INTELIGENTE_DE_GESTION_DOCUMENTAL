import difflib
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Max
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from auditoria.servicios import Accion, Resultado, registrar_auditoria
from usuarios.views import exigir_permiso

from .almacenamiento import (
    abrir_archivo,
    copiar_archivo,
    eliminar_archivo,
    guardar_archivo,
)
from .forms import NuevaVersionForm
from .models import Documento, VersionDocumento
from .permisos import documentos_visibles
from .trazabilidad import leer, serializar
from .views import (
    TAMANO_MAXIMO_TEXTO,
    _contexto,
    _decodificar_texto,
    _nombre_descarga,
    _tipo_vista_previa,
    _version_vigente,
)

logger = logging.getLogger(__name__)

DOCUMENTOS_POR_PAGINA = 15

# Solo estas acciones forman parte de la trazabilidad del documento.
EVENTOS = {
    Accion.DOCUMENTO_CARGAR: ("Documento creado", "bi-file-earmark-plus"),
    Accion.DOCUMENTO_MODIFICAR: ("Datos modificados", "bi-pencil"),
    Accion.VERSION_CREAR: ("Nueva versión del archivo", "bi-upload"),
    Accion.VERSION_RESTAURAR: ("Versión restaurada", "bi-arrow-counterclockwise"),
    Accion.DOCUMENTO_BAJA: ("Documento archivado", "bi-archive"),
    Accion.DOCUMENTO_REACTIVAR: ("Documento reactivado", "bi-arrow-repeat"),
}


# ==========================================================
# APOYO
# ==========================================================

def _versiones_ordenadas(documento):
    return list(
        documento.versiones
        .select_related("usuario", "formato")
        .order_by(F("numero_version").desc(nulls_last=True), "-pk")
    )


def _eventos(documento, versiones):
    """Línea de tiempo de cambios del documento, del más reciente al más antiguo."""
    por_numero = {v.numero_version: v for v in versiones if v.numero_version}

    registros = (
        documento.registros_auditoria
        .filter(accion__in=list(EVENTOS), resultado=Resultado.EXITOSO)
        .select_related("usuario")
        .order_by("-fecha_hora", "-pk")
    )

    eventos = []

    for registro in registros:
        titulo, icono = EVENTOS[registro.accion]
        datos = leer(registro.descripcion)

        evento = {
            "registro": registro,
            "titulo": titulo,
            "icono": icono,
            "cambios": [],
            "version": None,
            "origen": None,
            "comentario": "",
            "texto": "",
            "comparar": None,
        }

        if datos is None:
            evento["texto"] = registro.descripcion or ""
        else:
            evento["cambios"] = datos.get("cambios", [])
            evento["version"] = datos.get("version")
            evento["origen"] = datos.get("origen")
            evento["comentario"] = datos.get("comentario", "")

        numero = evento["version"]

        if isinstance(numero, int) and numero > 1:
            nueva = por_numero.get(numero)
            anterior = por_numero.get(numero - 1)

            if nueva and anterior:
                evento["comparar"] = (anterior.pk, nueva.pk)

        eventos.append(evento)

    return eventos


def _leer_texto(version):
    archivo = abrir_archivo(version.archivo)

    with archivo:
        contenido = archivo.read(TAMANO_MAXIMO_TEXTO + 1)

    truncado = len(contenido) > TAMANO_MAXIMO_TEXTO

    return _decodificar_texto(contenido[:TAMANO_MAXIMO_TEXTO], truncado)


def _diferencias(antes, despues):
    """Líneas agregadas, eliminadas y de contexto entre dos textos."""
    resultado = list(
        difflib.unified_diff(
            antes.splitlines(),
            despues.splitlines(),
            fromfile="A",
            tofile="B",
            lineterm="",
            n=2,
        )
    )[2:]  # se omiten las dos líneas de encabezado

    lineas = []

    for linea in resultado:
        if linea.startswith("@@"):
            lineas.append({"tipo": "sep", "texto": "· · ·"})
        elif linea.startswith("+"):
            lineas.append({"tipo": "add", "texto": linea[1:]})
        elif linea.startswith("-"):
            lineas.append({"tipo": "del", "texto": linea[1:]})
        else:
            lineas.append({"tipo": "ctx", "texto": linea[1:]})

    return lineas


# ==========================================================
# RESUMEN: DOCUMENTOS Y SUS VERSIONES
# ==========================================================

@login_required
def resumen_versiones(request):
    exigir_permiso(request.user, "version.consultar")

    documentos = (
        documentos_visibles(request.user)
        .annotate(
            total_versiones=Count("versiones"),
            ultima_version=Max("versiones__numero_version"),
            ultima_fecha=Max("versiones__fecha_creacion"),
        )
        .order_by(F("ultima_fecha").desc(nulls_last=True), "-pk")
    )

    pagina = Paginator(
        documentos,
        DOCUMENTOS_POR_PAGINA
    ).get_page(request.GET.get("pagina"))

    return render(
        request,
        "documentos/resumen_versiones.html",
        _contexto(request, pagina=pagina)
    )


# ==========================================================
# HISTORIAL DEL DOCUMENTO (versiones + línea de tiempo)
# ==========================================================

@login_required
def historial_versiones(request, documento_id):
    exigir_permiso(request.user, "version.consultar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    versiones = _versiones_ordenadas(documento)

    for version in versiones:
        version.previsualizable = _tipo_vista_previa(version) is not None

    return render(
        request,
        "documentos/historial_versiones.html",
        _contexto(
            request,
            documento=documento,
            versiones=versiones,
            vigente=versiones[0] if versiones else None,
            eventos=_eventos(documento, versiones),
        )
    )


# ==========================================================
# NUEVA VERSIÓN
# ==========================================================

@login_required
def nueva_version(request, documento_id):
    exigir_permiso(request.user, "documento.versionar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    if not documento.estado:
        messages.warning(
            request,
            "Un documento archivado no admite versiones nuevas. "
            "Reactívalo primero."
        )
        return redirect(
            "documentos:historial_versiones",
            documento_id=documento.pk
        )

    if request.method == "POST":
        formulario = NuevaVersionForm(request.POST, request.FILES)

        if formulario.is_valid():
            archivo = formulario.cleaned_data["archivo"]
            comentario = formulario.cleaned_data["comentario_cambio"]
            ruta = None

            try:
                with transaction.atomic():
                    doc = Documento.objects.select_for_update().get(
                        pk=documento.pk
                    )

                    ultimo = doc.versiones.aggregate(
                        maximo=Max("numero_version")
                    )["maximo"] or 0

                    numero = ultimo + 1

                    ruta = guardar_archivo(archivo, doc.pk, numero)

                    VersionDocumento.objects.create(
                        documento=doc,
                        usuario=request.user,
                        formato=formulario.formato,
                        numero_version=numero,
                        archivo=ruta,
                        comentario_cambio=comentario,
                    )

                    registrar_auditoria(
                        request.user,
                        Accion.VERSION_CREAR,
                        doc,
                        serializar({
                            "resumen": "Nueva versión %s de «%s»."
                                       % (numero, doc.titulo),
                            "version": numero,
                            "archivo": archivo.name,
                            "comentario": comentario,
                        })
                    )

            except Exception:
                logger.exception("Error al crear una nueva versión.")

                if ruta:
                    eliminar_archivo(ruta)

                messages.error(
                    request,
                    "No se pudo registrar la nueva versión. "
                    "Intenta de nuevo o contacta al administrador."
                )

            else:
                messages.success(
                    request,
                    "La versión %s de «%s» fue registrada correctamente."
                    % (numero, documento.titulo)
                )

                return redirect(
                    "documentos:historial_versiones",
                    documento_id=documento.pk
                )

    else:
        formulario = NuevaVersionForm()

    return render(
        request,
        "documentos/formulario_version.html",
        _contexto(request, formulario=formulario, documento=documento)
    )


# ==========================================================
# RESTAURAR UNA VERSIÓN ANTERIOR
# ==========================================================

@login_required
@require_POST
def restaurar_version(request, documento_id, version_id):
    exigir_permiso(request.user, "documento.versionar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    origen = get_object_or_404(documento.versiones, pk=version_id)

    destino = redirect(
        "documentos:historial_versiones",
        documento_id=documento.pk
    )

    if not documento.estado:
        messages.warning(
            request,
            "Un documento archivado no se puede modificar. Reactívalo primero."
        )
        return destino

    vigente = _version_vigente(documento)

    if vigente is not None and vigente.pk == origen.pk:
        messages.info(request, "Esa ya es la versión vigente.")
        return destino

    if not origen.archivo:
        messages.error(request, "Esa versión no tiene un archivo disponible.")
        return destino

    ruta = None

    try:
        with transaction.atomic():
            doc = Documento.objects.select_for_update().get(pk=documento.pk)

            ultimo = doc.versiones.aggregate(
                maximo=Max("numero_version")
            )["maximo"] or 0

            numero = ultimo + 1

            ruta = copiar_archivo(origen.archivo, doc.pk, numero)

            VersionDocumento.objects.create(
                documento=doc,
                usuario=request.user,
                formato=origen.formato,
                numero_version=numero,
                archivo=ruta,
                comentario_cambio="Restaurada desde la versión %s."
                                  % origen.numero_version,
            )

            registrar_auditoria(
                request.user,
                Accion.VERSION_RESTAURAR,
                doc,
                serializar({
                    "resumen": "Se restauró la versión %s de «%s» como "
                               "versión %s."
                               % (origen.numero_version, doc.titulo, numero),
                    "version": numero,
                    "origen": origen.numero_version,
                })
            )

    except Exception:
        logger.exception("Error al restaurar una versión.")

        if ruta:
            eliminar_archivo(ruta)

        messages.error(
            request,
            "No se pudo restaurar la versión. "
            "Intenta de nuevo o contacta al administrador."
        )

    else:
        messages.success(
            request,
            "La versión %s se restauró como versión %s."
            % (origen.numero_version, numero)
        )

    return destino


# ==========================================================
# VER Y DESCARGAR UNA VERSIÓN ESPECÍFICA
# ==========================================================

@login_required
@never_cache
@xframe_options_sameorigin
def vista_previa_version(request, documento_id, version_id):
    # Entrega el contenido del archivo, así que exige el mismo
    # permiso que la descarga.
    exigir_permiso(request.user, "documento.descargar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    version = get_object_or_404(documento.versiones, pk=version_id)

    tipo = _tipo_vista_previa(version)

    if tipo is None:
        return HttpResponse(
            "La vista previa no está disponible para este formato.",
            status=415,
            content_type="text/plain; charset=utf-8"
        )

    categoria, content_type = tipo

    try:
        archivo = abrir_archivo(version.archivo)

    except OSError:
        logger.exception("No se pudo abrir la versión %s.", version.pk)

        return HttpResponse(
            "El archivo no está disponible en este momento.",
            status=404,
            content_type="text/plain; charset=utf-8"
        )

    if categoria == "texto":
        with archivo:
            contenido = archivo.read(TAMANO_MAXIMO_TEXTO + 1)

        truncado = len(contenido) > TAMANO_MAXIMO_TEXTO
        texto = _decodificar_texto(contenido[:TAMANO_MAXIMO_TEXTO], truncado)

        if truncado:
            texto += (
                "\n\n[Vista previa recortada. Descarga el archivo "
                "para ver el contenido completo.]"
            )

        return HttpResponse(texto, content_type=content_type)

    return FileResponse(
        archivo,
        content_type=content_type,
        filename=_nombre_descarga(documento, version)
    )


@login_required
def descargar_version(request, documento_id, version_id):
    exigir_permiso(request.user, "documento.descargar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    version = get_object_or_404(documento.versiones, pk=version_id)

    if not version.archivo:
        messages.error(request, "Esta versión no tiene un archivo disponible.")
        return redirect(
            "documentos:historial_versiones",
            documento_id=documento.pk
        )

    try:
        archivo = abrir_archivo(version.archivo)

    except OSError:
        logger.exception(
            "No se pudo abrir la versión %s del documento %s.",
            version.pk, documento.pk
        )

        registrar_auditoria(
            request.user,
            Accion.VERSION_DESCARGAR,
            documento,
            "Descarga fallida de la versión %s de «%s»: archivo no disponible."
            % (version.numero_version, documento.titulo),
            Resultado.ERROR
        )

        messages.error(
            request,
            "El archivo no está disponible en este momento. "
            "Contacta al administrador."
        )

        return redirect(
            "documentos:historial_versiones",
            documento_id=documento.pk
        )

    registrar_auditoria(
        request.user,
        Accion.VERSION_DESCARGAR,
        documento,
        "Descarga de la versión %s del documento «%s»."
        % (version.numero_version, documento.titulo)
    )

    return FileResponse(
        archivo,
        as_attachment=True,
        filename=_nombre_descarga(documento, version)
    )

# ==========================================================
# COMPARAR DOS VERSIONES
# ==========================================================

TAMANO_MAXIMO_OFFICE = 10 * 1024 * 1024
MAX_LINEAS_COMPARACION = 5000
MAX_FILAS_HOJA = 2000
EXTENSIONES_COMPARABLES = (".txt", ".docx", ".xlsx", ".pptx")


def _extension(version):
    nombre = version.archivo or ""
    return "." + nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""


def _lineas_docx(contenido):
    from io import BytesIO
    from docx import Document

    documento = Document(BytesIO(contenido))

    lineas = [parrafo.text for parrafo in documento.paragraphs]

    for tabla in documento.tables:
        lineas.append("[Tabla]")

        for fila in tabla.rows:
            lineas.append(
                " | ".join(celda.text.strip() for celda in fila.cells)
            )

    return lineas


def _lineas_xlsx(contenido):
    from io import BytesIO
    from openpyxl import load_workbook

    libro = load_workbook(BytesIO(contenido), read_only=True, data_only=True)
    lineas = []

    try:
        for hoja in libro.worksheets:
            lineas.append("[Hoja: %s]" % hoja.title)

            for numero, fila in enumerate(
                hoja.iter_rows(values_only=True), start=1
            ):
                if numero > MAX_FILAS_HOJA:
                    lineas.append("[... hoja recortada ...]")
                    break

                celdas = ["" if c is None else str(c) for c in fila]

                while celdas and celdas[-1] == "":
                    celdas.pop()

                if celdas:
                    lineas.append(" | ".join(celdas))
    finally:
        libro.close()

    return lineas


def _lineas_pptx(contenido):
    from io import BytesIO
    from pptx import Presentation

    presentacion = Presentation(BytesIO(contenido))
    lineas = []

    for numero, diapositiva in enumerate(presentacion.slides, start=1):
        lineas.append("[Diapositiva %d]" % numero)

        for forma in diapositiva.shapes:
            if not forma.has_text_frame:
                continue

            for parrafo in forma.text_frame.paragraphs:
                texto = "".join(run.text for run in parrafo.runs).strip()

                if texto:
                    lineas.append(texto)

    return lineas


def _extraer_texto(version):
    """Texto de una versión para compararla (txt, docx, xlsx o pptx)."""
    extension = _extension(version)

    if extension == ".txt":
        return _leer_texto(version)

    with abrir_archivo(version.archivo) as archivo:
        contenido = archivo.read(TAMANO_MAXIMO_OFFICE + 1)

    if len(contenido) > TAMANO_MAXIMO_OFFICE:
        raise ValueError("El archivo es demasiado grande para compararlo.")

    if extension == ".docx":
        lineas = _lineas_docx(contenido)
    elif extension == ".xlsx":
        lineas = _lineas_xlsx(contenido)
    elif extension == ".pptx":
        lineas = _lineas_pptx(contenido)
    else:
        raise ValueError("Formato no comparable.")

    return "\n".join(lineas[:MAX_LINEAS_COMPARACION])

import re
from difflib import SequenceMatcher

from django.utils.html import escape
from django.utils.safestring import mark_safe

CONTEXTO_COMPARACION = 2
_TOKENS = re.compile(r"\s+|\w+|[^\w\s]", re.UNICODE)


def _html_linea(texto):
    if texto == "":
        return mark_safe('<span class="linea-vacia">(línea vacía)</span>')

    return escape(texto)


def _html_palabras(izquierda, derecha):
    """Resalta solo las palabras que cambiaron entre dos líneas."""
    tokens_a = _TOKENS.findall(izquierda)
    tokens_b = _TOKENS.findall(derecha)

    html_a, html_b = [], []

    for op, i1, i2, j1, j2 in SequenceMatcher(
        None, tokens_a, tokens_b, autojunk=False
    ).get_opcodes():
        parte_a = escape("".join(tokens_a[i1:i2]))
        parte_b = escape("".join(tokens_b[j1:j2]))

        if op == "equal":
            html_a.append(parte_a)
            html_b.append(parte_b)
            continue

        if parte_a:
            html_a.append('<mark class="pal-del">%s</mark>' % parte_a)

        if parte_b:
            html_b.append('<mark class="pal-add">%s</mark>' % parte_b)

    return mark_safe("".join(html_a)), mark_safe("".join(html_b))


def _comparacion_lado_a_lado(texto_a, texto_b):
    """
    Devuelve (filas, resumen) para mostrar la comparación en dos columnas.
    Las líneas sin cambios lejanas a una modificación se agrupan en una
    fila plegable.
    """
    lineas_a = texto_a.splitlines()
    lineas_b = texto_b.splitlines()

    filas = []
    resumen = {"agregadas": 0, "eliminadas": 0, "modificadas": 0}

    for op, i1, i2, j1, j2 in SequenceMatcher(
        None, lineas_a, lineas_b, autojunk=False
    ).get_opcodes():

        if op == "equal":
            for k in range(i2 - i1):
                filas.append({
                    "clase": "igual",
                    "num_a": i1 + k + 1,
                    "num_b": j1 + k + 1,
                    "html_a": _html_linea(lineas_a[i1 + k]),
                    "html_b": _html_linea(lineas_b[j1 + k]),
                })
            continue

        izquierda = lineas_a[i1:i2]
        derecha = lineas_b[j1:j2]

        for k in range(max(len(izquierda), len(derecha))):
            a = izquierda[k] if k < len(izquierda) else None
            b = derecha[k] if k < len(derecha) else None

            fila = {
                "num_a": i1 + k + 1 if a is not None else "",
                "num_b": j1 + k + 1 if b is not None else "",
                "html_a": "",
                "html_b": "",
            }

            if a is not None and b is not None:
                fila["clase"] = "mod"
                resumen["modificadas"] += 1

                if (
                    a.strip()
                    and b.strip()
                    and SequenceMatcher(None, a, b).ratio() >= 0.5
                ):
                    fila["html_a"], fila["html_b"] = _html_palabras(a, b)
                else:
                    fila["html_a"] = _html_linea(a)
                    fila["html_b"] = _html_linea(b)

            elif a is not None:
                fila["clase"] = "del"
                fila["html_a"] = _html_linea(a)
                resumen["eliminadas"] += 1

            else:
                fila["clase"] = "add"
                fila["html_b"] = _html_linea(b)
                resumen["agregadas"] += 1

            filas.append(fila)

    resumen["iguales"] = sum(1 for f in filas if f["clase"] == "igual")

    # Filas visibles: las que tienen cambios y su contexto cercano.
    visibles = set()

    for i, fila in enumerate(filas):
        if fila["clase"] != "igual":
            visibles.update(range(
                max(0, i - CONTEXTO_COMPARACION),
                min(len(filas), i + CONTEXTO_COMPARACION + 1)
            ))

    resultado = []
    grupo = 0
    i = 0

    while i < len(filas):
        if i in visibles:
            resultado.append(filas[i])
            i += 1
            continue

        j = i
        while j < len(filas) and j not in visibles:
            j += 1

        grupo += 1
        resultado.append({
            "clase": "plegado",
            "cantidad": j - i,
            "grupo": grupo,
        })

        for fila in filas[i:j]:
            fila["grupo"] = grupo
            resultado.append(fila)

        i = j

    # Marca el inicio de cada zona con cambios, para navegar entre ellas.
    zonas = 0
    en_cambio = False

    for fila in resultado:
        es_cambio = fila["clase"] in ("mod", "add", "del")

        if es_cambio and not en_cambio:
            zonas += 1
            fila["inicio"] = True
            fila["ancla"] = zonas

        en_cambio = es_cambio

    resumen["zonas"] = zonas

    return resultado, resumen


@login_required
def comparar_versiones(request, documento_id):
    exigir_permiso(request.user, "version.consultar")
    exigir_permiso(request.user, "documento.descargar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    versiones = _versiones_ordenadas(documento)
    por_id = {str(v.pk): v for v in versiones}

    b = por_id.get(request.GET.get("b")) or (
        versiones[0] if versiones else None
    )
    a = por_id.get(request.GET.get("a")) or (
        versiones[1] if len(versiones) > 1 else None
    )

    if a is None or b is None or a.pk == b.pk:
        messages.info(
            request,
            "Se necesitan al menos dos versiones distintas para comparar."
        )
        return redirect(
            "documentos:historial_versiones",
            documento_id=documento.pk
        )

    # A siempre es la más antigua y B la más reciente.
    if (a.numero_version or 0) > (b.numero_version or 0):
        a, b = b, a

    tipo_a = _tipo_vista_previa(a)
    tipo_b = _tipo_vista_previa(b)

    modo = "ninguno"
    filas = []
    resumen = {}
    error = None

    if (
        _extension(a) in EXTENSIONES_COMPARABLES
        and _extension(b) in EXTENSIONES_COMPARABLES
    ):
        try:
            filas, resumen = _comparacion_lado_a_lado(
                _extraer_texto(a),
                _extraer_texto(b)
            )
            modo = "texto"

        except Exception:
            logger.exception("No se pudieron comparar las versiones.")
            error = (
                "No se pudo leer el contenido de alguno de los archivos. "
                "Descárgalos para compararlos."
            )

    elif tipo_a and tipo_b:
        modo = "visual"

    plantilla = (
        "documentos/comparar_texto.html"
        if modo == "texto"
        else "documentos/comparar_versiones.html"
    )

    return render(
        request,
        plantilla,
        _contexto(
            request,
            documento=documento,
            versiones=versiones,
            a=a,
            b=b,
            modo=modo,
            filas=filas,
            resumen=resumen,
            diferencias=[],
            error=error,
            categoria_a=tipo_a[0] if tipo_a else None,
            categoria_b=tipo_b[0] if tipo_b else None,
        )
    )

# ==========================================================
# ACCESOS AL DOCUMENTO (descargas, vistas previas, consultas)
# ==========================================================

from django.core.paginator import Paginator
from django.db.models import F

from auditoria.models import RegistroAuditoria
from auditoria.servicios import Accion

ACCESOS_POR_PAGINA = 20

FILTROS_ACCESO = {
    "": (
        "Descargas y vistas previas",
        (Accion.DOCUMENTO_DESCARGAR, Accion.DOCUMENTO_VISTA_PREVIA),
    ),
    "descargas": ("Solo descargas", (Accion.DOCUMENTO_DESCARGAR,)),
    "vistas": ("Solo vistas previas", (Accion.DOCUMENTO_VISTA_PREVIA,)),
    "consultas": ("Consultas del detalle", (Accion.DOCUMENTO_CONSULTAR,)),
}

DATOS_ACCESO = {
    Accion.DOCUMENTO_DESCARGAR: ("Descarga", "bi-download", "acc-descarga"),
    Accion.DOCUMENTO_VISTA_PREVIA: ("Vista previa", "bi-eye", "acc-vista"),
    Accion.DOCUMENTO_CONSULTAR: ("Consulta", "bi-journal-text", "acc-consulta"),
}


@login_required
def accesos_documento(request, documento_id):
    exigir_permiso(request.user, "auditoria.consultar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    base = RegistroAuditoria.objects.filter(documento=documento)

    filtro = request.GET.get("tipo", "")
    if filtro not in FILTROS_ACCESO:
        filtro = ""

    por_tipo = base.filter(accion__in=FILTROS_ACCESO[filtro][1])

    # Usuarios que aparecen con el tipo de acceso elegido.
    usuarios = []

    for fila in (
        por_tipo
        .values(
            "usuario_id",
            "usuario__username",
            "usuario__first_name",
            "usuario__last_name",
        )
        .distinct()
        .order_by("usuario__username")
    ):
        nombre = (
            "%s %s" % (fila["usuario__first_name"], fila["usuario__last_name"])
        ).strip()

        usuarios.append({
            "id": fila["usuario_id"],
            "nombre": nombre or fila["usuario__username"],
        })

    registros = por_tipo.select_related("usuario", "usuario__area")

    usuario_id = request.GET.get("usuario", "")
    if usuario_id.isdigit():
        registros = registros.filter(usuario_id=int(usuario_id))
    else:
        usuario_id = ""

    registros = registros.order_by(
        F("fecha_hora").desc(nulls_last=True), "-pk"
    )

    pagina = Paginator(
        registros,
        ACCESOS_POR_PAGINA
    ).get_page(request.GET.get("pagina"))

    filas = list(pagina.object_list)

    for registro in filas:
        etiqueta, icono, clase = DATOS_ACCESO.get(
            registro.accion,
            (registro.accion or "—", "bi-dot", "acc-otro")
        )
        registro.etiqueta = etiqueta
        registro.icono = icono
        registro.clase = clase

    ultimo = (
        base.filter(accion__in=FILTROS_ACCESO[""][1])
        .select_related("usuario")
        .order_by(F("fecha_hora").desc(nulls_last=True), "-pk")
        .first()
    )

    parametros = request.GET.copy()
    parametros.pop("pagina", None)

    return render(
        request,
        "documentos/accesos_documento.html",
        _contexto(
            request,
            documento=documento,
            pagina=pagina,
            filas=filas,
            opciones=[
                (clave, datos[0]) for clave, datos in FILTROS_ACCESO.items()
            ],
            filtro=filtro,
            usuarios=usuarios,
            usuario_id=usuario_id,
            total_descargas=base.filter(
                accion=Accion.DOCUMENTO_DESCARGAR
            ).count(),
            total_vistas=base.filter(
                accion=Accion.DOCUMENTO_VISTA_PREVIA
            ).count(),
            ultimo=ultimo,
            consulta=parametros.urlencode(),
        )
    )

# ==========================================================
# REGISTRO DE LAS DESCARGAS HECHAS DESDE EL HISTORIAL
# ==========================================================

from functools import wraps

from auditoria.servicios import Accion, registrar_auditoria

_descargar_version_sin_registro = descargar_version


@wraps(_descargar_version_sin_registro)
def descargar_version(request, *args, **kwargs):
    """Descarga una versión y deja constancia en la auditoría."""
    respuesta = _descargar_version_sin_registro(request, *args, **kwargs)

    # Solo se registra si la descarga se entregó correctamente.
    if getattr(respuesta, "status_code", None) != 200:
        return respuesta

    try:
        datos = request.resolver_match.kwargs if request.resolver_match else {}

        documento = Documento.objects.filter(
            pk=datos.get("documento_id")
        ).first()

        if documento is not None:
            version = None

            if datos.get("version_id") is not None:
                version = VersionDocumento.objects.filter(
                    pk=datos["version_id"],
                    documento=documento
                ).first()

            numero = (
                " (versión %s)" % version.numero_version
                if version is not None and version.numero_version
                else ""
            )

            registrar_auditoria(
                request.user,
                Accion.DOCUMENTO_DESCARGAR,
                documento,
                "Descarga desde el historial del documento «%s»%s."
                % (documento.titulo, numero)
            )

    except Exception:
        # Un fallo al registrar nunca debe impedir la descarga.
        logger.exception("No se pudo registrar la descarga de una versión.")

    return respuesta