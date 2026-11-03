import json
from datetime import date


def serializar(datos):
    """Convierte un diccionario en texto JSON legible."""
    return json.dumps(datos, ensure_ascii=False)


def leer(descripcion):
    """Devuelve el diccionario guardado, o None si es texto simple."""
    try:
        datos = json.loads(descripcion or "")
    except (TypeError, ValueError):
        return None

    return datos if isinstance(datos, dict) else None


def _legible(campo, valor):
    if valor is None or valor == "":
        return "—"

    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")

    queryset = getattr(campo, "queryset", None)

    if queryset is not None:
        pk = getattr(valor, "pk", valor)
        objeto = queryset.model._default_manager.filter(pk=pk).first()
        return str(objeto) if objeto is not None else str(pk)

    return str(valor)


def describir_modificacion(formulario, documento):
    """
    Compara los valores originales del formulario con los nuevos y
    devuelve el detalle del cambio listo para guardarse en la bitácora.
    """
    cambios = []

    for nombre in formulario.changed_data:
        campo = formulario.fields[nombre]

        cambios.append({
            "campo": str(campo.label or nombre),
            "antes": _legible(campo, formulario.initial.get(nombre)),
            "despues": _legible(campo, formulario.cleaned_data.get(nombre)),
        })

    return serializar({
        "resumen": "Datos modificados de «%s»." % documento.titulo,
        "cambios": cambios,
    })