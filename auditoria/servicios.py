"""
Registro de acciones en la tabla RegistroAuditoria.

Uso:
    from auditoria.servicios import Accion, Resultado, registrar_auditoria

    registrar_auditoria(request.user, Accion.DOCUMENTO_CARGAR, documento,
                        "Carga del documento ...")
"""

from .models import RegistroAuditoria


class Resultado:
    EXITOSO = "exitoso"
    DENEGADO = "denegado"
    ERROR = "error"


class Accion:
    DOCUMENTO_CARGAR = "documento.cargar"
    DOCUMENTO_CONSULTAR = "documento.consultar"
    DOCUMENTO_DESCARGAR = "documento.descargar"
    DOCUMENTO_VISTA_PREVIA = "documento.vista_previa"
    DOCUMENTO_MODIFICAR = "documento.modificar"
    DOCUMENTO_BAJA = "documento.archivar"
    DOCUMENTO_REACTIVAR = "documento.reactivar"


def registrar_auditoria(usuario, accion, documento=None,
                        descripcion="", resultado=Resultado.EXITOSO):
    """
    Crea un registro de auditoría.

    Cuando se llama dentro de un bloque transaction.atomic(), el registro
    se confirma o se revierte junto con la operación auditada.
    """
    return RegistroAuditoria.objects.create(
        usuario=usuario,
        documento=documento,
        accion=accion[:100],
        descripcion=descripcion,
        resultado=resultado[:50],
    )
