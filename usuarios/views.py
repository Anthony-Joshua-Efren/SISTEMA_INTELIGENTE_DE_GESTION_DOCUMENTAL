from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import UsuarioCrearForm, UsuarioEditarForm
from .models import Usuario, Area, Rol


# ==========================================================
# DESCRIPCIONES DE LOS ROLES
# ==========================================================

DESCRIPCIONES_ROLES = {
    "administrador": (
        "Control total del sistema. Administra usuarios, áreas, "
        "roles, permisos, documentos, auditoría y configuración."
    ),
    "responsable de área": (
        "Supervisa la documentación de su área, coordina "
        "actividades y realiza las operaciones autorizadas."
    ),
    "colaborador": (
        "Carga, consulta y administra documentos de acuerdo "
        "con los permisos asignados a su rol."
    ),
    "consulta": (
        "Consulta los documentos autorizados sin modificar "
        "su contenido."
    ),
}


def es_rol_administrador(rol):
    return (
        (rol.nombre or "").strip().casefold()
        == "administrador"
    )


# ==========================================================
# ENTRADA AL SISTEMA
# ==========================================================

def entrada(request):
    if request.user.is_authenticated:
        return redirect("usuarios:inicio")

    return redirect("usuarios:login")


# ==========================================================
# VALIDACIÓN DE ROL ACTIVO
# ==========================================================

def validar_rol_activo(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        raise PermissionDenied(
            "Tu cuenta no está habilitada."
        )

    if usuario.rol_id and not usuario.rol.estado:
        raise PermissionDenied(
            "Tu rol está desactivado. Contacta al administrador."
        )


# ==========================================================
# PERMISOS DEL USUARIO
# ==========================================================

def obtener_permisos(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        return set()

    if not usuario.rol_id:
        return set()

    if not usuario.rol.estado:
        return set()

    return set(
        usuario.rol.rolpermiso_set.values_list(
            "permiso__codigo",
            flat=True
        )
    )


def obtener_modulos(usuario):
    permisos = obtener_permisos(usuario)

    return {
        "usuarios": any(
            permiso.startswith(("usuario.", "area.", "rol."))
            for permiso in permisos
        ),

        "gestion_documental": any(
            permiso.startswith("documento.")
            for permiso in permisos
        ),

        "organizacion_busqueda": any(
            permiso.startswith("documento.")
            for permiso in permisos
        ),

        "versiones": any(
            permiso.startswith("version.")
            for permiso in permisos
        ),

        "revisiones": any(
            permiso.startswith(("revision.", "alerta."))
            or permiso == "reporte.generar"
            for permiso in permisos
        ),

        "inteligencia": any(
            permiso.startswith("inteligencia.")
            for permiso in permisos
        ),

        "configuracion": "catalogo.administrar" in permisos,
    }


def exigir_permiso(usuario, codigo):
    validar_rol_activo(usuario)

    permisos = obtener_permisos(usuario)

    if codigo not in permisos:
        raise PermissionDenied(
            "No tienes autorización para realizar esta operación."
        )


# ==========================================================
# DASHBOARD
# ==========================================================

@login_required
def inicio(request):
    validar_rol_activo(request.user)

    return render(
        request,
        "usuarios/inicio.html",
        {
            "modulos": obtener_modulos(request.user),
        }
    )


# ==========================================================
# GESTIÓN DE USUARIOS
# ==========================================================

@login_required
def gestion_usuarios(request):
    validar_rol_activo(request.user)

    modulos = obtener_modulos(request.user)

    if not modulos["usuarios"]:
        raise PermissionDenied(
            "No tienes autorización para acceder a este módulo."
        )

    usuarios = Usuario.objects.select_related(
        "area",
        "rol"
    ).order_by("id")

    areas = Area.objects.all().order_by("nombre")

    roles = list(
        Rol.objects.all().order_by("nombre")
    )

    for rol in roles:
        nombre = (rol.nombre or "").strip().casefold()

        rol.descripcion_funciones = (
            DESCRIPCIONES_ROLES.get(
                nombre,
                rol.descripcion or
                "Rol del sistema con permisos configurables."
            )
        )

        rol.es_administrador = es_rol_administrador(rol)

    return render(
        request,
        "usuarios/gestion_usuarios.html",
        {
            "usuarios": usuarios,
            "areas": areas,
            "roles": roles,
            "modulos": modulos,
            "permisos_usuario": obtener_permisos(request.user),
        }
    )


# ==========================================================
# CREAR USUARIO
# ==========================================================

@login_required
def crear_usuario(request):
    exigir_permiso(request.user, "usuario.crear")

    if request.method == "POST":
        formulario = UsuarioCrearForm(request.POST)

        if formulario.is_valid():
            with transaction.atomic():
                usuario = formulario.save()

            messages.success(
                request,
                f"El usuario {usuario.username} fue creado correctamente."
            )

            return redirect("usuarios:gestion_usuarios")

    else:
        formulario = UsuarioCrearForm()

    return render(
        request,
        "usuarios/formulario_usuario.html",
        {
            "formulario": formulario,
            "titulo": "Nuevo usuario",
            "accion": "Crear usuario",
            "modulos": obtener_modulos(request.user),
        }
    )


# ==========================================================
# EDITAR USUARIO
# ==========================================================

@login_required
def editar_usuario(request, usuario_id):
    exigir_permiso(request.user, "usuario.modificar")

    usuario = get_object_or_404(
        Usuario,
        pk=usuario_id
    )

    if request.method == "POST":
        formulario = UsuarioEditarForm(
            request.POST,
            instance=usuario
        )

        if formulario.is_valid():
            with transaction.atomic():
                formulario.save()

            messages.success(
                request,
                f"El usuario {usuario.username} fue actualizado correctamente."
            )

            return redirect("usuarios:gestion_usuarios")

    else:
        formulario = UsuarioEditarForm(instance=usuario)

    return render(
        request,
        "usuarios/formulario_usuario.html",
        {
            "formulario": formulario,
            "titulo": "Editar usuario",
            "accion": "Guardar cambios",
            "usuario_editado": usuario,
            "modulos": obtener_modulos(request.user),
        }
    )


# ==========================================================
# DESACTIVAR USUARIO
# ==========================================================

@login_required
@require_POST
def desactivar_usuario(request, usuario_id):
    exigir_permiso(request.user, "usuario.desactivar")

    with transaction.atomic():
        usuario = get_object_or_404(
            Usuario.objects.select_for_update(),
            pk=usuario_id
        )

        if usuario.pk == request.user.pk:
            messages.error(
                request,
                "No puedes desactivar tu propia cuenta."
            )

        elif not usuario.is_active:
            messages.warning(
                request,
                "Este usuario ya se encuentra desactivado."
            )

        else:
            usuario.is_active = False
            usuario.save(update_fields=["is_active"])

            messages.success(
                request,
                f"El usuario {usuario.username} fue desactivado."
            )

    return redirect("usuarios:gestion_usuarios")


# ==========================================================
# REACTIVAR USUARIO
# ==========================================================

@login_required
@require_POST
def reactivar_usuario(request, usuario_id):
    exigir_permiso(request.user, "usuario.desactivar")

    with transaction.atomic():
        usuario = get_object_or_404(
            Usuario.objects.select_for_update(),
            pk=usuario_id
        )

        if usuario.is_active:
            messages.warning(
                request,
                "Este usuario ya se encuentra activo."
            )

        else:
            usuario.is_active = True
            usuario.save(update_fields=["is_active"])

            messages.success(
                request,
                f"El usuario {usuario.username} fue reactivado."
            )

    return redirect("usuarios:gestion_usuarios")


# ==========================================================
# ACTIVAR / DESACTIVAR ROLES
# ==========================================================

@login_required
@require_POST
def cambiar_estado_rol(request, rol_id):
    exigir_permiso(request.user, "rol.administrar")

    with transaction.atomic():
        rol = get_object_or_404(
            Rol.objects.select_for_update(),
            pk=rol_id
        )

        # El Administrador nunca se puede desactivar.
        if es_rol_administrador(rol):
            messages.error(
                request,
                "El rol Administrador está protegido "
                "y no puede cambiar de estado."
            )

            return redirect("usuarios:gestion_usuarios")

        nuevo_estado = not rol.estado

        rol.estado = nuevo_estado
        rol.save(update_fields=["estado"])

        if nuevo_estado:
            messages.success(
                request,
                f"El rol {rol.nombre} fue activado correctamente."
            )
        else:
            messages.success(
                request,
                f"El rol {rol.nombre} fue desactivado correctamente."
            )

    return redirect("usuarios:gestion_usuarios")


# ==========================================================
# ACTIVAR / DESACTIVAR ÁREAS
# ==========================================================

@login_required
@require_POST
def cambiar_estado_area(request, area_id):
    exigir_permiso(request.user, "area.administrar")

    with transaction.atomic():
        area = get_object_or_404(
            Area.objects.select_for_update(),
            pk=area_id
        )

        area.estado = not area.estado
        area.save(update_fields=["estado"])

        accion = "activada" if area.estado else "desactivada"
        messages.success(
            request,
            f"El área {area.nombre} fue {accion} correctamente."
        )

    return redirect("usuarios:gestion_usuarios")
