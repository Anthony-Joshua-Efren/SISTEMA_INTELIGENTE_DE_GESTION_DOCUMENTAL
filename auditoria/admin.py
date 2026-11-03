from django.contrib import admin
from .models import RegistroAuditoria, Alerta


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('id_registro', 'usuario', 'accion', 'fecha_hora', 'resultado')
    list_filter = ('accion', 'resultado')
    search_fields = ('descripcion',)

    # La bitácora es de solo lectura: nadie puede agregar,
    # modificar ni borrar registros desde el panel de administración.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('id_alerta', 'documento', 'tipo', 'fecha_objetivo', 'estado')
    list_filter = ('tipo', 'estado')