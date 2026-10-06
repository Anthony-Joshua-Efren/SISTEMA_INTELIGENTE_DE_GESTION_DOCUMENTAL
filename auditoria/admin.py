from django.contrib import admin
from .models import RegistroAuditoria, Alerta


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('id_registro', 'usuario', 'accion', 'fecha_hora', 'resultado')
    list_filter = ('accion', 'resultado')
    search_fields = ('descripcion',)


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('id_alerta', 'documento', 'tipo', 'fecha_objetivo', 'estado')
    list_filter = ('tipo', 'estado')