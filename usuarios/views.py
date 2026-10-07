from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import RolPermiso


@login_required
def inicio(request):
    usuario = request.user

    permisos = set()

    if usuario.rol:
        permisos = set(
            usuario.rol.rolpermiso_set.values_list(
                'permiso__codigo',
                flat=True
            )
        )

    modulos = {
        'usuarios': any(
            permiso.startswith('usuario.') or
            permiso.startswith('area.') or
            permiso.startswith('rol.')
            for permiso in permisos
        ),

        'gestion_documental': any(
            permiso.startswith('documento.')
            for permiso in permisos
        ),

        'organizacion_busqueda': any(
            permiso.startswith('documento.')
            for permiso in permisos
        ),

        'versiones': any(
            permiso.startswith('version.')
            for permiso in permisos
        ),

        'revisiones': any(
            permiso.startswith('revision.') or
            permiso.startswith('alerta.') or
            permiso == 'reporte.generar'
            for permiso in permisos
        ),

        'inteligencia': any(
            permiso.startswith('inteligencia.')
            for permiso in permisos
        ),

        'configuracion': (
            'catalogo.administrar' in permisos
        ),
    }

    return render(
        request,
        'usuarios/inicio.html',
        {
            'modulos': modulos,
        }
    )