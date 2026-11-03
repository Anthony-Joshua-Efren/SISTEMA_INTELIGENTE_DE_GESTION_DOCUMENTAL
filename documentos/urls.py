from django.urls import path

from . import versiones, views

app_name = "documentos"

urlpatterns = [

    # ==========================================
    # LISTADO Y CARGA
    # ==========================================

    path(
        "",
        views.lista_documentos,
        name="lista_documentos"
    ),

    path(
        "nuevo/",
        views.cargar_documento,
        name="cargar_documento"
    ),

    # ==========================================
    # VERSIONES Y TRAZABILIDAD
    # ==========================================

    path(
        "versiones/",
        versiones.resumen_versiones,
        name="resumen_versiones"
    ),

    path(
        "<int:documento_id>/versiones/",
        versiones.historial_versiones,
        name="historial_versiones"
    ),

    path(
        "<int:documento_id>/versiones/nueva/",
        versiones.nueva_version,
        name="nueva_version"
    ),

    path(
        "<int:documento_id>/versiones/<int:version_id>/descargar/",
        versiones.descargar_version,
        name="descargar_version"
    ),

    path(
        "<int:documento_id>/versiones/<int:version_id>/vista-previa/",
        versiones.vista_previa_version,
        name="vista_previa_version"
    ),

    path(
        "<int:documento_id>/versiones/<int:version_id>/restaurar/",
        versiones.restaurar_version,
        name="restaurar_version"
    ),

    path(
        "<int:documento_id>/versiones/comparar/",
        versiones.comparar_versiones,
        name="comparar_versiones"
    ),

    # ==========================================
    # DETALLE, EDICIÓN Y DESCARGA
    # ==========================================

    path(
        "<int:documento_id>/",
        views.detalle_documento,
        name="detalle_documento"
    ),

    path(
        "<int:documento_id>/editar/",
        views.editar_documento,
        name="editar_documento"
    ),

    path(
        "<int:documento_id>/descargar/",
        views.descargar_documento,
        name="descargar_documento"
    ),

    path(
        "<int:documento_id>/vista-previa/",
        views.vista_previa_documento,
        name="vista_previa_documento"
    ),

    # ==========================================
    # ARCHIVAR / REACTIVAR
    # ==========================================

    path(
        "<int:documento_id>/cambiar-estado/",
        views.cambiar_estado_documento,
        name="cambiar_estado_documento"
    ),
    path(
        "<int:documento_id>/versiones/accesos/",
        versiones.accesos_documento,
        name="accesos_documento"
    ),
]