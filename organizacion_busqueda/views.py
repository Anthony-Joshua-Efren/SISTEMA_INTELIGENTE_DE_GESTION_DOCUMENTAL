from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.shortcuts import render

from documentos.models import Categoria, Documento, TipoDocumento
from documentos.permisos import documentos_visibles
from usuarios.models import Area
from usuarios.views import exigir_permiso, obtener_modulos, obtener_permisos


@login_required
def organizacion_busqueda(request):
    exigir_permiso(request.user, "documento.consultar")

    documentos = (
        documentos_visibles(request.user)
        .select_related(
            "area",
            "categoria",
            "tipo_documento",
            "usuario_responsable",
        )
    )

    # Parámetros de búsqueda y filtros
    busqueda = request.GET.get("q", "").strip()
    categoria = request.GET.get("categoria", "")
    area = request.GET.get("area", "")
    tipo = request.GET.get("tipo", "")
    estado = request.GET.get("estado", "")
    fecha_desde = request.GET.get("fecha_desde", "")
    fecha_hasta = request.GET.get("fecha_hasta", "")
    orden = request.GET.get("orden", "recientes")

    # Búsqueda general
    if busqueda:
        documentos = documentos.filter(
            Q(titulo__icontains=busqueda)
            | Q(descripcion__icontains=busqueda)
            | Q(proveedor__icontains=busqueda)
            | Q(sistema_relacionado__icontains=busqueda)
            | Q(departamento__icontains=busqueda)
            | Q(categoria__nombre__icontains=busqueda)
            | Q(tipo_documento__nombre__icontains=busqueda)
            | Q(area__nombre__icontains=busqueda)
        )

    # Filtros
    if categoria:
        documentos = documentos.filter(categoria_id=categoria)

    if area:
        documentos = documentos.filter(area_id=area)

    if tipo:
        documentos = documentos.filter(tipo_documento_id=tipo)

    if estado == "activo":
        documentos = documentos.filter(estado=True)
    elif estado == "archivado":
        documentos = documentos.filter(estado=False)

    if fecha_desde:
        documentos = documentos.filter(fecha_documento__gte=fecha_desde)

    if fecha_hasta:
        documentos = documentos.filter(fecha_documento__lte=fecha_hasta)

    # Ordenamiento
    if orden == "antiguos":
        documentos = documentos.order_by(
            F("fecha_carga").asc(nulls_last=True),
            "pk"
        )
    elif orden == "az":
        documentos = documentos.order_by("titulo", "pk")
    elif orden == "za":
        documentos = documentos.order_by("-titulo", "-pk")
    else:
        documentos = documentos.order_by(
            F("fecha_carga").desc(nulls_last=True),
            "-pk"
        )

    pagina = Paginator(documentos, 15).get_page(
        request.GET.get("pagina")
    )

    contexto = {
        "modulos": obtener_modulos(request.user),
        "permisos_usuario": obtener_permisos(request.user),
        "pagina": pagina,
        "total_resultados": documentos.count(),
        "categorias": Categoria.objects.filter(estado=True).order_by("nombre"),
        "areas": Area.objects.filter(estado=True).order_by("nombre"),
        "tipos_documento": TipoDocumento.objects.filter(
            estado=True
        ).order_by("nombre"),
        "filtros": {
            "q": busqueda,
            "categoria": categoria,
            "area": area,
            "tipo": tipo,
            "estado": estado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "orden": orden,
        },
    }

    return render(
        request,
        "organizacion_busqueda/organizacion_busqueda.html",
        contexto
    )
