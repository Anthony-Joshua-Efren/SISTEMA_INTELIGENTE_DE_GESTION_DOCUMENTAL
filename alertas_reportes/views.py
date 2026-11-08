
import csv
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.http import HttpResponse
from django.utils import timezone

from usuarios.views import obtener_modulos, obtener_permisos, validar_rol_activo, exigir_permiso
from documentos.permisos import documentos_visibles

@login_required
def inicio(request):
    validar_rol_activo(request.user)

    modulos = obtener_modulos(request.user)
    permisos = obtener_permisos(request.user)
    if not modulos["revisiones"]:
        raise PermissionDenied(
            "No tienes autorización para acceder a este módulo."
        )
    documentos = []
    if "documento.consultar" in permisos and "alerta.consultar" in permisos:
        documentos = documentos_visibles(request.user)

    hoy = timezone.localdate()
    limite_aviso = hoy + timedelta(days=7)

    total_documentos = len(documentos)
    
    documentos_vencidos = sum(
        1 for documento in documentos
        if documento.fecha_vencimiento
        and documento.fecha_vencimiento < hoy
    )

    proximos_vencer = sum(
        1 for documento in documentos
        if documento.fecha_vencimiento
        and hoy < documento.fecha_vencimiento <= limite_aviso
    )

    revisiones_pendientes = sum(
        1 for documento in documentos
        if documento.fecha_revision
        and documento.fecha_revision < hoy
    )

    return render(
        request,
        "alertas_reportes/inicio.html",
        {
            "modulos": modulos,
            "documentos": documentos,
            "hoy": hoy,
            "limite_aviso": limite_aviso,
            "total_documentos": total_documentos,
            "documentos_vencidos": documentos_vencidos,
            "proximos_vencer": proximos_vencer,
            "revisiones_pendientes": revisiones_pendientes,
            "puede_descargar_reporte": "reporte.generar" in permisos and "documento.consultar" in permisos,
        }
    )


@login_required
def descargar_reporte(request):
    exigir_permiso(request.user, "reporte.generar")
    exigir_permiso(request.user, "documento.consultar")

    documentos = documentos_visibles(request.user)

    hoy = timezone.localdate()
    limite_aviso = hoy + timedelta(days=7)

    respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = 'attachment; filename="reporte_documental.csv"'
    
    respuesta.write("\ufeff")
    escritor = csv.writer(respuesta, delimiter=";")

    escritor.writerow([
        "Documento",
        "Fecha de revisión",
        "Fecha de vencimiento",
        "Situación",
    ])

    
    for documento in documentos:
        if documento.fecha_vencimiento and documento.fecha_vencimiento < hoy:
            situacion = "Vencido"
        elif documento.fecha_vencimiento == hoy:
            situacion = "Vence hoy"
        elif documento.fecha_vencimiento and hoy < documento.fecha_vencimiento <= limite_aviso:
            situacion = "Próximo a vencer"
        elif documento.fecha_revision and documento.fecha_revision < hoy:
            situacion = "Fecha de revisión pasada"
        elif documento.fecha_revision == hoy:
            situacion = "Revisión programada hoy"
        elif not documento.fecha_revision and not documento.fecha_vencimiento:
            situacion = "Sin fechas registradas"
        else:
            situacion = "Sin fechas vencidas"
    
        escritor.writerow([
            documento.titulo or "Sin título",
            documento.fecha_revision.strftime("%d/%m/%Y") if documento.fecha_revision else "",
            documento.fecha_vencimiento.strftime("%d/%m/%Y") if documento.fecha_vencimiento else "",
            situacion,
        ])


    return respuesta
