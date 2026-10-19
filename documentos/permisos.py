
from usuarios.views import es_rol_administrador, obtener_permisos

from .models import Documento


def es_administrador(usuario):
    return bool(usuario.rol_id) and es_rol_administrador(usuario.rol)


def documentos_visibles(usuario):
    consulta = Documento.objects.select_related(
        "area",
        "categoria",
        "tipo_documento",
        "usuario_responsable",
    )

    if not usuario.is_authenticated or not usuario.is_active:
        return consulta.none()

    if es_administrador(usuario):
        visibles = consulta
    elif usuario.area_id:
        visibles = consulta.filter(area_id=usuario.area_id)
    else:
        return consulta.none()

    if "documento.archivar" not in obtener_permisos(usuario):
        visibles = visibles.filter(estado=True)

    return visibles
