
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    # URL principal del sistema
    path(
        '',
        views.entrada,
        name='entrada'
    ),

    # Inicio de sesión
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='usuarios/login.html',
            redirect_authenticated_user=True
        ),
        name='login'
    ),

    # Dashboard protegido
    path(
        'inicio/',
        views.inicio,
        name='inicio'
    ),

    # Cierre de sesión
    path(
        'logout/',
        auth_views.LogoutView.as_view(
            next_page='usuarios:login'
        ),
        name='logout'
    ),
]
