"""Administrator-only configuration using existing permission helpers."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from documentos.forms import TAMANO_MAXIMO_MB
from documentos.permisos import es_administrador
from documentos.views import DOCUMENTOS_POR_PAGINA
from usuarios.views import exigir_permiso, obtener_modulos

from .forms import CategoriaForm, FormatoArchivoForm, TipoDocumentoForm

CATALOGOS = {
    "categorias": {"titulo": "Categorías", "form": CategoriaForm, "icono": "bi-tags"},
    "tipos": {"titulo": "Tipos documentales", "form": TipoDocumentoForm, "icono": "bi-files"},
    "formatos": {"titulo": "Formatos de archivo", "form": FormatoArchivoForm, "icono": "bi-file-earmark"},
}


def administrador_autorizado(view):
    @never_cache
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        exigir_permiso(request.user, "catalogo.administrar")
        if not es_administrador(request.user):
            raise PermissionDenied("Solo el Administrador autorizado puede acceder a Configuración.")
        return view(request, *args, **kwargs)

    return wrapped


def _catalogo(key):
    try:
        return CATALOGOS[key]
    except KeyError:
        raise Http404("Catálogo no encontrado.") from None


def _contexto(request, **extra):
    return {"modulos": obtener_modulos(request.user), "catalogos": CATALOGOS, **extra}


@administrador_autorizado
@require_GET
def inicio(request):
    return render(request, "configuracion/inicio.html", _contexto(
        request, tamano_maximo_mb=TAMANO_MAXIMO_MB,
        documentos_por_pagina=DOCUMENTOS_POR_PAGINA,
    ))


@administrador_autorizado
@require_GET
def catalogo(request, catalogo):
    definition = _catalogo(catalogo)
    records = definition["form"]._meta.model.objects.order_by("nombre", "pk")
    page = Paginator(records, 20).get_page(request.GET.get("page"))
    return render(request, "configuracion/catalogo.html", _contexto(
        request, catalogo=catalogo, definicion=definition, pagina=page,
    ))


@administrador_autorizado
@require_http_methods(["GET", "POST"])
def formulario(request, catalogo, pk=None):
    definition = _catalogo(catalogo)
    form_class = definition["form"]
    instance = get_object_or_404(form_class._meta.model, pk=pk) if pk is not None else None
    form = form_class(request.POST if request.method == "POST" else None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Registro actualizado correctamente." if instance else "Registro creado correctamente.")
        return redirect("configuracion:catalogo", catalogo=catalogo)
    return render(request, "configuracion/formulario_catalogo.html", _contexto(
        request, catalogo=catalogo, definicion=definition, form=form,
        titulo="Editar registro" if instance else "Crear registro",
    ))


@administrador_autorizado
@require_http_methods(["GET", "POST"])
def estado(request, catalogo, pk, accion):
    definition = _catalogo(catalogo)
    if accion not in ("activar", "desactivar"):
        raise Http404("Operación no encontrada.")
    instance = get_object_or_404(definition["form"]._meta.model, pk=pk)
    if request.method == "POST":
        instance.estado = accion == "activar"
        instance.save(update_fields=["estado"])
        messages.success(request, "Registro activado correctamente." if instance.estado else "Registro desactivado correctamente.")
        return redirect("configuracion:catalogo", catalogo=catalogo)
    return render(request, "configuracion/confirmar_estado.html", _contexto(
        request, catalogo=catalogo, definicion=definition, registro=instance, accion=accion,
    ))
