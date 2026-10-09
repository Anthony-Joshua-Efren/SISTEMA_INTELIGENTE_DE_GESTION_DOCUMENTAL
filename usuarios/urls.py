
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "usuarios"

urlpatterns = [

    # ==========================================
    # ENTRADA PRINCIPAL
    # ==========================================

    path(
        "",
        views.entrada,
        name="entrada"
    ),

    # ==========================================
    # AUTENTICACIÓN
    # ==========================================

    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="usuarios/login.html",
            redirect_authenticated_user=True
        ),
        name="login"
    ),

    path(
        "logout/",
        auth_views.LogoutView.as_view(
            next_page="usuarios:login"
        ),
        name="logout"
    ),

    # ==========================================
    # DASHBOARD
    # ==========================================

    path(
        "inicio/",
        views.inicio,
        name="inicio"
    ),

    # ==========================================
    # GESTIÓN DE USUARIOS
    # ==========================================

    path(
        "usuarios/",
        views.gestion_usuarios,
        name="gestion_usuarios"
    ),

    path(
        "usuarios/nuevo/",
        views.crear_usuario,
        name="crear_usuario"
    ),

    path(
        "usuarios/<int:usuario_id>/editar/",
        views.editar_usuario,
        name="editar_usuario"
    ),

    path(
        "usuarios/<int:usuario_id>/desactivar/",
        views.desactivar_usuario,
        name="desactivar_usuario"
    ),

    path(
        "usuarios/<int:usuario_id>/reactivar/",
        views.reactivar_usuario,
        name="reactivar_usuario"
    ),

    # ==========================================
    # ACTIVAR / DESACTIVAR ROLES
    # ==========================================

    path(
        "roles/<int:rol_id>/cambiar-estado/",
        views.cambiar_estado_rol,
        name="cambiar_estado_rol"
    ),

    # ==========================================
    # ACTIVAR / DESACTIVAR ÁREAS
    # ==========================================

    path(
        "areas/<int:area_id>/cambiar-estado/",
        views.cambiar_estado_area,
        name="cambiar_estado_area"
    ),

]
