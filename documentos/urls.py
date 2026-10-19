from django.urls import path

from . import views

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

]
