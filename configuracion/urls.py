from django.urls import path

from . import views

app_name = "configuracion"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("catalogos/<slug:catalogo>/", views.catalogo, name="catalogo"),
    path("catalogos/<slug:catalogo>/crear/", views.formulario, name="crear"),
    path("catalogos/<slug:catalogo>/<int:pk>/editar/", views.formulario, name="editar"),
    path("catalogos/<slug:catalogo>/<int:pk>/estado/<slug:accion>/", views.estado, name="estado"),
]
