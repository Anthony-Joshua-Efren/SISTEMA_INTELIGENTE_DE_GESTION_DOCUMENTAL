
from django.urls import path

from . import views

app_name = "alertas_reportes"

urlpatterns = [
    path("", views.inicio, name="panel_alertas_reportes"),
    path("descargar-reporte/", views.descargar_reporte, name="descargar_reporte"),
]
