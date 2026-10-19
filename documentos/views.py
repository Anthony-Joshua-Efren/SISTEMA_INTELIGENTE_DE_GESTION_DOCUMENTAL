import logging
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousFileOperation
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, OuterRef, Subquery
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_POST

from auditoria.servicios import Accion, Resultado, registrar_auditoria
from usuarios.views import (
    exigir_permiso,
    obtener_modulos,
    obtener_permisos,
)

from .almacenamiento import abrir_archivo, eliminar_archivo, guardar_archivo
from .forms import DocumentoCargarForm, DocumentoForm
from .models import Documento, VersionDocumento
from .permisos import documentos_visibles, es_administrador

logger = logging.getLogger(__name__)

DOCUMENTOS_POR_PAGINA = 15

# Formatos con vista previa dentro del navegador (lista cerrada).
# No se incluyen SVG ni HTML, porque podrían ejecutar código.
TIPOS_VISTA_PREVIA = {
    ".pdf": ("pdf", "application/pdf"),
    ".jpg": ("imagen", "image/jpeg"),
    ".jpeg": ("imagen", "image/jpeg"),
    ".png": ("imagen", "image/png"),
    ".gif": ("imagen", "image/gif"),
    ".webp": ("imagen", "image/webp"),
    ".txt": ("texto", "text/plain; charset=utf-8"),
}

TAMANO_MAXIMO_TEXTO = 2 * 1024 * 1024


# ==========================================================
# APOYO
# ==========================================================

def _contexto(request, **extra):
    contexto = {
        "modulos": obtener_modulos(request.user),
        "permisos_usuario": obtener_permisos(request.user),
    }
    contexto.update(extra)
    return contexto


def _version_vigente(documento):
    """La versión vigente es la de mayor número."""
    return (
        documento.versiones
        .select_related("usuario", "formato")
        .order_by(F("numero_version").desc(nulls_last=True), "-pk")
        .first()
    )


def _tipo_vista_previa(version):
    """Devuelve (categoría, content-type) o None si no hay vista previa."""
    if version is None or not version.archivo:
        return None

    return TIPOS_VISTA_PREVIA.get(Path(version.archivo).suffix.lower())


def _nombre_descarga(documento, version):
    return "%s_v%s%s" % (
        slugify(documento.titulo or "") or "documento",
        version.numero_version or 1,
        Path(version.archivo).suffix,
    )


def _decodificar_texto(contenido, truncado):
    """UTF-8 si es posible; si no, Windows-1252 (Bloc de notas en español)."""
    for recorte in range(4 if truncado else 1):
        parte = contenido[:len(contenido) - recorte]

        try:
            return parte.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue

    return contenido.decode("cp1252", errors="replace")


# ==========================================================
# LISTADO
# ==========================================================

@login_required
def lista_documentos(request):
    exigir_permiso(request.user, "documento.consultar")

    # Datos de la versión vigente (la de mayor número) de cada documento.
    vigente = (
        VersionDocumento.objects
        .filter(documento=OuterRef("pk"))
        .order_by(F("numero_version").desc(nulls_last=True), "-pk")
    )

    documentos = (
        documentos_visibles(request.user)
        .annotate(
            version_actual=Subquery(vigente.values("numero_version")[:1]),
            formato_extension=Subquery(vigente.values("formato__extension")[:1]),
        )
        .order_by(F("fecha_carga").desc(nulls_last=True), "-pk")
    )

    pagina = Paginator(
        documentos,
        DOCUMENTOS_POR_PAGINA
    ).get_page(request.GET.get("pagina"))

    return render(
        request,
        "documentos/lista_documentos.html",
        _contexto(request, pagina=pagina)
    )


# ==========================================================
# CARGAR DOCUMENTO
# ==========================================================

@login_required
def cargar_documento(request):
    exigir_permiso(request.user, "documento.cargar")

    if not es_administrador(request.user) and not request.user.area_id:
        messages.error(
            request,
            "Tu usuario no tiene un área asignada, por lo que no puede "
            "cargar documentos. Contacta al administrador."
        )
        return redirect("documentos:lista_documentos")

    if request.method == "POST":
        formulario = DocumentoCargarForm(
            request.POST,
            request.FILES,
            usuario=request.user
        )

        if formulario.is_valid():
            archivo = formulario.cleaned_data["archivo"]
            ruta = None

            try:
                with transaction.atomic():
                    documento = formulario.save(commit=False)
                    documento.usuario_responsable = request.user
                    documento.estado = True
                    documento.save()

                    ruta = guardar_archivo(archivo, documento.pk, 1)

                    VersionDocumento.objects.create(
                        documento=documento,
                        usuario=request.user,
                        formato=formulario.formato,
                        numero_version=1,
                        archivo=ruta,
                        comentario_cambio="Versión inicial",
                    )

                    registrar_auditoria(
                        request.user,
                        Accion.DOCUMENTO_CARGAR,
                        documento,
                        "Carga del documento «%s» (versión 1, archivo %s)."
                        % (documento.titulo, archivo.name)
                    )

            except Exception:
                logger.exception("Error al cargar un documento.")

                # Si el archivo ya se guardó pero la base de datos
                # revirtió la operación, se elimina para no dejar basura.
                if ruta:
                    eliminar_archivo(ruta)

                messages.error(
                    request,
                    "No se pudo cargar el documento. "
                    "Intenta de nuevo o contacta al administrador."
                )

            else:
                messages.success(
                    request,
                    "El documento «%s» fue cargado correctamente."
                    % documento.titulo
                )

                return redirect(
                    "documentos:detalle_documento",
                    documento_id=documento.pk
                )

    else:
        formulario = DocumentoCargarForm(usuario=request.user)

    return render(
        request,
        "documentos/formulario_documento.html",
        _contexto(
            request,
            formulario=formulario,
            titulo="Cargar documento",
            subtitulo="Registra los datos del documento y adjunta su archivo.",
            accion="Cargar documento",
            es_carga=True,
        )
    )


# ==========================================================
# DETALLE
# ==========================================================

@login_required
def detalle_documento(request, documento_id):
    exigir_permiso(request.user, "documento.consultar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    registrar_auditoria(
        request.user,
        Accion.DOCUMENTO_CONSULTAR,
        documento,
        "Consulta del documento «%s»." % documento.titulo
    )

    version = _version_vigente(documento)
    tipo = _tipo_vista_previa(version)

    return render(
        request,
        "documentos/detalle_documento.html",
        _contexto(
            request,
            documento=documento,
            version=version,
            tipo_vista_previa=tipo[0] if tipo else None,
            total_versiones=documento.versiones.count(),
        )
    )


# ==========================================================
# EDITAR DOCUMENTO
# ==========================================================

@login_required
def editar_documento(request, documento_id):
    exigir_permiso(request.user, "documento.modificar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    if not documento.estado:
        messages.warning(
            request,
            "Un documento archivado no se puede modificar. "
            "Reactívalo primero."
        )
        return redirect(
            "documentos:detalle_documento",
            documento_id=documento.pk
        )

    # Se guarda antes de que el formulario modifique el objeto.
    titulo_original = documento.titulo

    if request.method == "POST":
        formulario = DocumentoForm(
            request.POST,
            instance=documento,
            usuario=request.user
        )

        if formulario.is_valid():
            if not formulario.has_changed():
                messages.info(request, "No se realizaron cambios.")

                return redirect(
                    "documentos:detalle_documento",
                    documento_id=documento.pk
                )

            campos = ", ".join(
                str(formulario.fields[nombre].label or nombre)
                for nombre in formulario.changed_data
            )

            with transaction.atomic():
                formulario.save()

                registrar_auditoria(
                    request.user,
                    Accion.DOCUMENTO_MODIFICAR,
                    documento,
                    "Modificación del documento «%s». Campos: %s."
                    % (documento.titulo, campos)
                )

            messages.success(
                request,
                "El documento «%s» fue actualizado correctamente."
                % documento.titulo
            )

            return redirect(
                "documentos:detalle_documento",
                documento_id=documento.pk
            )

    else:
        formulario = DocumentoForm(
            instance=documento,
            usuario=request.user
        )

    return render(
        request,
        "documentos/formulario_documento.html",
        _contexto(
            request,
            formulario=formulario,
            titulo="Editar documento",
            subtitulo=titulo_original or "Documento sin título",
            accion="Guardar cambios",
            es_carga=False,
            documento_id=documento_id,
        )
    )


# ==========================================================
# DESCARGAR DOCUMENTO
# ==========================================================

@login_required
def descargar_documento(request, documento_id):
    exigir_permiso(request.user, "documento.descargar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    version = _version_vigente(documento)

    if version is None or not version.archivo:
        messages.error(
            request,
            "Este documento no tiene un archivo disponible."
        )
        return redirect(
            "documentos:detalle_documento",
            documento_id=documento.pk
        )

    try:
        archivo = abrir_archivo(version.archivo)

    except (OSError, SuspiciousFileOperation):
        logger.exception(
            "No se pudo abrir el archivo del documento %s.", documento.pk
        )

        registrar_auditoria(
            request.user,
            Accion.DOCUMENTO_DESCARGAR,
            documento,
            "Descarga fallida del documento «%s»: archivo no disponible."
            % documento.titulo,
            Resultado.ERROR
        )

        messages.error(
            request,
            "El archivo no está disponible en este momento. "
            "Contacta al administrador."
        )

        return redirect(
            "documentos:detalle_documento",
            documento_id=documento.pk
        )

    # La descarga se registra antes de entregar el archivo.
    registrar_auditoria(
        request.user,
        Accion.DOCUMENTO_DESCARGAR,
        documento,
        "Descarga del documento «%s» (versión %s)."
        % (documento.titulo, version.numero_version)
    )

    nombre = _nombre_descarga(documento, version)

    return FileResponse(archivo, as_attachment=True, filename=nombre)


# ==========================================================
# VISTA PREVIA (PDF, imágenes y texto)
# ==========================================================

@login_required
@never_cache
@xframe_options_sameorigin
def vista_previa_documento(request, documento_id):
    # La vista previa entrega el contenido del archivo, por eso
    # exige el mismo permiso que la descarga.
    exigir_permiso(request.user, "documento.descargar")

    documento = get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    version = _version_vigente(documento)
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

    except (OSError, SuspiciousFileOperation):
        logger.exception(
            "No se pudo abrir el archivo del documento %s.", documento.pk
        )

        registrar_auditoria(
            request.user,
            Accion.DOCUMENTO_VISTA_PREVIA,
            documento,
            "Vista previa fallida del documento «%s»: archivo no disponible."
            % documento.titulo,
            Resultado.ERROR
        )

        return HttpResponse(
            "El archivo no está disponible en este momento.",
            status=404,
            content_type="text/plain; charset=utf-8"
        )

    registrar_auditoria(
        request.user,
        Accion.DOCUMENTO_VISTA_PREVIA,
        documento,
        "Vista previa del documento «%s» (versión %s)."
        % (documento.titulo, version.numero_version)
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


# ==========================================================
# ARCHIVAR / REACTIVAR (baja lógica)
# ==========================================================

@login_required
@require_POST
def cambiar_estado_documento(request, documento_id):
    exigir_permiso(request.user, "documento.archivar")

    # Verifica que el documento sea visible para el usuario.
    get_object_or_404(
        documentos_visibles(request.user),
        pk=documento_id
    )

    accion = request.POST.get("accion")

    if accion not in ("archivar", "reactivar"):
        messages.error(request, "Operación no válida.")
        return redirect(
            "documentos:detalle_documento",
            documento_id=documento_id
        )

    with transaction.atomic():
        documento = Documento.objects.select_for_update().get(
            pk=documento_id
        )

        nuevo_estado = accion == "reactivar"

        if documento.estado == nuevo_estado:
            messages.warning(
                request,
                "El documento ya se encuentra %s."
                % ("activo" if nuevo_estado else "archivado")
            )

        else:
            documento.estado = nuevo_estado
            documento.save(update_fields=["estado"])

            registrar_auditoria(
                request.user,
                (
                    Accion.DOCUMENTO_REACTIVAR
                    if nuevo_estado
                    else Accion.DOCUMENTO_BAJA
                ),
                documento,
                "%s del documento «%s»."
                % (
                    "Reactivación" if nuevo_estado else "Archivado",
                    documento.titulo,
                )
            )

            messages.success(
                request,
                "El documento «%s» fue %s."
                % (
                    documento.titulo,
                    "reactivado" if nuevo_estado else "archivado",
                )
            )

    return redirect(
        "documentos:detalle_documento",
        documento_id=documento_id
    )
