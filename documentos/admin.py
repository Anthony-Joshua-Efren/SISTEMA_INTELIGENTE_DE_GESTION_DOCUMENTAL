from django.contrib import admin
from .models import (
    Categoria, Etiqueta, TipoDocumento, FormatoArchivo,
    Documento, DocumentoEtiqueta, VersionDocumento,
    PermisoDocumento, SugerenciaInteligente
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id_categoria', 'nombre', 'estado')
    list_filter = ('estado',)


@admin.register(Etiqueta)
class EtiquetaAdmin(admin.ModelAdmin):
    list_display = ('id_etiqueta', 'nombre')


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ('id_tipo_documento', 'nombre', 'estado')
    list_filter = ('estado',)


@admin.register(FormatoArchivo)
class FormatoArchivoAdmin(admin.ModelAdmin):
    list_display = ('id_formato', 'nombre', 'extension', 'estado')
    list_filter = ('estado',)


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('id_documento', 'titulo', 'area', 'categoria', 'tipo_documento', 'estado')
    list_filter = ('area', 'categoria', 'tipo_documento', 'estado')
    search_fields = ('titulo', 'descripcion', 'proveedor')


@admin.register(VersionDocumento)
class VersionDocumentoAdmin(admin.ModelAdmin):
    list_display = ('id_version', 'documento', 'numero_version', 'usuario', 'fecha_creacion')
    list_filter = ('documento',)


@admin.register(SugerenciaInteligente)
class SugerenciaInteligenteAdmin(admin.ModelAdmin):
    list_display = ('id_sugerencia', 'documento', 'tipo_sugerencia', 'valor_sugerido', 'estado_decision')


# Registros simples
admin.site.register(DocumentoEtiqueta)
admin.site.register(PermisoDocumento)