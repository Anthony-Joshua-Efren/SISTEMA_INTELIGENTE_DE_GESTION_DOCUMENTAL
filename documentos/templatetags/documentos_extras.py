from datetime import timezone as dt_timezone

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def hora_local(valor):
    """
    Muestra una fecha y hora en la zona horaria del proyecto.

    Las columnas "timestamp without time zone" de Supabase regresan
    fechas sin zona horaria, guardadas en UTC. Esas fechas se tratan
    como UTC y se convierten a la hora local (America/Mexico_City).
    """
    if valor is None or valor == "":
        return valor

    if timezone.is_naive(valor):
        valor = timezone.make_aware(valor, dt_timezone.utc)

    return timezone.localtime(valor)


ICONOS_FORMATO = {
    "pdf": "bi-file-earmark-pdf",
    "jpg": "bi-file-earmark-image",
    "jpeg": "bi-file-earmark-image",
    "png": "bi-file-earmark-image",
    "gif": "bi-file-earmark-image",
    "webp": "bi-file-earmark-image",
    "txt": "bi-file-earmark-text",
    "doc": "bi-file-earmark-word",
    "docx": "bi-file-earmark-word",
    "xls": "bi-file-earmark-excel",
    "xlsx": "bi-file-earmark-excel",
    "csv": "bi-file-earmark-excel",
    "ppt": "bi-file-earmark-ppt",
    "pptx": "bi-file-earmark-ppt",
    "zip": "bi-file-earmark-zip",
    "rar": "bi-file-earmark-zip",
}


def _limpiar_extension(extension):
    return (extension or "").strip().lstrip(".").lower()


@register.filter
def icono_formato(extension):
    """Clase de Bootstrap Icons según la extensión (pdf, png, docx...)."""
    return ICONOS_FORMATO.get(_limpiar_extension(extension), "bi-file-earmark")


@register.filter
def etiqueta_formato(extension):
    """Extensión en mayúsculas, sin punto: PDF, PNG, DOCX."""
    return _limpiar_extension(extension).upper()
