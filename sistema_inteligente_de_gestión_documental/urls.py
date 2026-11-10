"""
URL configuration for sistema_inteligente_de_gestión_documental project.

The urlpatterns list routes URLs to views.
For more information please see:
https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('documentos/', include('documentos.urls')),
    path('organizacion-busqueda/', include('organizacion_busqueda.urls')),
    path('revisiones-alertas-reportes/', include('alertas_reportes.urls')),
    path('asistencia-inteligente/', include('asistencia_inteligente.urls')),
]