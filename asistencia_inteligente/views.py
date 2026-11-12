from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from documentos.models import SugerenciaInteligente
from documentos.permisos import documentos_visibles
from usuarios.views import exigir_permiso, obtener_modulos, obtener_permisos

from .servicios import ACEPTADA, MODIFICADA, RECHAZADA, generar_sugerencias

PERMISO = "inteligencia.utilizar"

CAMPOS = (
    "titulo",
    "descripcion",
    "proveedor",
    "sistema_relacionado",
    "departamento",
    "tipo_documento",
)


@login_required
@require_POST
@never_cache
def sugerir(request):
    """
    Devuelve en JSON la categoría y las etiquetas sugeridas para los datos
    que el usuario lleva capturados. Solo sugiere: no guarda nada.

    Requiere el permiso de funciones inteligentes y poder cargar o
    modificar documentos.
    """
    exigir_permiso(request.user, PERMISO)

    try:
        exigir_permiso(request.user, "documento.cargar")
    except PermissionDenied:
        exigir_permiso(request.user, "documento.modificar")

    datos = {campo: (request.POST.get(campo) or "").strip() for campo in CAMPOS}
    archivo = request.FILES.get("archivo")

    if not any(datos.values()) and archivo is None:
        return JsonResponse({
            "categoria": None,
            "etiquetas": [],
            "usa_contenido": False,
            "mensaje": "Captura al menos el título o selecciona un archivo.",
        })

    resultado = generar_sugerencias(request.user, datos, archivo)

    if resultado["categoria"] is None and not resultado["etiquetas"]:
        resultado["mensaje"] = (
            "No hay una sugerencia confiable. Puedes clasificar el documento "
            "manualmente."
        )

    return JsonResponse(resultado)


@login_required
def panel(request):
    """Resumen de cómo se están usando las sugerencias (solo documentos visibles)."""
    exigir_permiso(request.user, PERMISO)

    sugerencias = (
        SugerenciaInteligente.objects
        .filter(documento__in=documentos_visibles(request.user))
        .select_related("documento", "usuario")
        .order_by("-fecha_generacion", "-pk")
    )

    conteo = {
        fila["estado_decision"]: fila["total"]
        for fila in sugerencias.values("estado_decision").annotate(total=Count("pk"))
    }
    total = sum(conteo.values())

    def porcentaje(estado):
        return round(conteo.get(estado, 0) * 100 / total) if total else 0

    pagina = Paginator(sugerencias, 15).get_page(request.GET.get("pagina"))

    return render(request, "asistencia_inteligente/panel_resumen.html", {
        "modulos": obtener_modulos(request.user),
        "permisos_usuario": obtener_permisos(request.user),
        "pagina": pagina,
        "total": total,
        "aceptadas": conteo.get(ACEPTADA, 0),
        "modificadas": conteo.get(MODIFICADA, 0),
        "rechazadas": conteo.get(RECHAZADA, 0),
        "pct_aceptadas": porcentaje(ACEPTADA),
        "pct_modificadas": porcentaje(MODIFICADA),
        "pct_rechazadas": porcentaje(RECHAZADA),
    })
