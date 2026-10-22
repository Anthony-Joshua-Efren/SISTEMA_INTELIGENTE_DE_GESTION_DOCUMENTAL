from django.urls import path

from . import views

app_name = "organizacion_busqueda"

urlpatterns = [
    path(
        "",
        views.organizacion_busqueda,
        name="organizacion_busqueda"
    ),
]