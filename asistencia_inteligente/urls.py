from django.urls import path

from . import views

app_name = "asistencia_inteligente"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("sugerir/", views.sugerir, name="sugerir"),
]
