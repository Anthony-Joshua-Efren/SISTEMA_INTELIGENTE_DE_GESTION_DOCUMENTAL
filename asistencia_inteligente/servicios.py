"""
Conexión del motor con la base de datos del sistema.

Reglas del cuestionario aplicadas aquí:
  * La sugerencia es solo informativa; nada se asigna sin decisión del
    usuario (preguntas 13 y 14).
  * Solo se guarda lo que el usuario confirma en el formulario.
  * Para aprender de documentos ya existentes se usan únicamente los que
    el usuario puede ver (`documentos_visibles`).
  * La decisión (aceptar, modificar o rechazar) queda en
    SugerenciaInteligente y en la auditoría.
"""

from django.db import transaction

from auditoria.servicios import registrar_auditoria
from documentos.models import (
    Categoria,
    Documento,
    DocumentoEtiqueta,
    Etiqueta,
    SugerenciaInteligente,
    TipoDocumento,
)
from documentos.permisos import documentos_visibles
from usuarios.views import obtener_permisos

from . import catalogo, motor
from .extraccion import extraer_texto, nombre_a_texto

ACCION_AUDITORIA = "sugerencia.resolver"

TIPO_CATEGORIA = "categoria"
TIPO_ETIQUETA = "etiqueta"

ACEPTADA = "aceptada"
MODIFICADA = "modificada"
RECHAZADA = "rechazada"

EJEMPLOS_POR_GRUPO = 30


def _texto_ejemplo(documento):
    return " ".join(filter(None, [
        documento.titulo,
        documento.descripcion,
        documento.proveedor,
        documento.sistema_relacionado,
    ]))


# ----------------------------------------------------------
# Candidatos
# ----------------------------------------------------------

def _candidatos_categoria(usuario):
    categorias = list(Categoria.objects.filter(estado=True))
    ejemplos = {c.pk: [] for c in categorias}

    recientes = documentos_visibles(usuario).order_by("-pk")[:500]
    for documento in recientes:
        lista = ejemplos.get(documento.categoria_id)
        if lista is not None and len(lista) < EJEMPLOS_POR_GRUPO:
            lista.append(_texto_ejemplo(documento))

    return [
        motor.Candidato(
            id=c.pk,
            nombre=c.nombre or "",
            descripcion=c.descripcion or "",
            palabras_clave=catalogo.PALABRAS_CLAVE_CATEGORIA.get(
                motor.normalizar(c.nombre), []
            ),
            ejemplos=ejemplos[c.pk],
        )
        for c in categorias
        if c.nombre
    ]


def _candidatos_etiqueta(usuario):
    etiquetas = list(Etiqueta.objects.all())
    ejemplos = {e.pk: [] for e in etiquetas}

    visibles = documentos_visibles(usuario).values_list("pk", flat=True)
    relaciones = (
        DocumentoEtiqueta.objects
        .filter(documento_id__in=visibles)
        .select_related("documento")
        .order_by("-documento_id")[:1000]
    )
    for relacion in relaciones:
        lista = ejemplos.get(relacion.etiqueta_id)
        if lista is not None and len(lista) < EJEMPLOS_POR_GRUPO:
            lista.append(_texto_ejemplo(relacion.documento))

    return [
        motor.Candidato(
            id=e.pk,
            nombre=e.nombre or "",
            descripcion=e.descripcion or "",
            palabras_clave=catalogo.PALABRAS_CLAVE_ETIQUETA.get(
                motor.normalizar(e.nombre), []
            ),
            ejemplos=ejemplos[e.pk],
        )
        for e in etiquetas
        if e.nombre
    ]


# ----------------------------------------------------------
# Generar sugerencias
# ----------------------------------------------------------

def generar_sugerencias(usuario, datos, archivo=None):
    """
    `datos`: dict con titulo, descripcion, proveedor, sistema_relacionado,
    departamento y tipo_documento (id). `archivo`: UploadedFile opcional.

    Devuelve {"categoria": dict|None, "etiquetas": [dict], "usa_contenido": bool}
    """
    tipo = TipoDocumento.objects.filter(pk=datos.get("tipo_documento") or None).first()

    contenido = ""
    nombre_archivo = ""
    if archivo is not None:
        nombre_archivo = archivo.name
        archivo.seek(0)
        contenido = extraer_texto(archivo.name, archivo.read())
        archivo.seek(0)

    campos = {
        "titulo": datos.get("titulo", ""),
        "descripcion": datos.get("descripcion", ""),
        "proveedor": datos.get("proveedor", ""),
        "sistema_relacionado": datos.get("sistema_relacionado", ""),
        "departamento": datos.get("departamento", ""),
        "tipo_documento": (tipo.nombre or "") if tipo else "",
        "nombre_archivo": nombre_a_texto(nombre_archivo),
        "contenido": contenido,
    }

    categoria = motor.sugerir_categoria(_candidatos_categoria(usuario), campos)
    etiquetas = motor.sugerir_etiquetas(_candidatos_etiqueta(usuario), campos)

    return {
        "categoria": categoria.como_diccionario() if categoria else None,
        "etiquetas": [e.como_diccionario() for e in etiquetas],
        "usa_contenido": bool(contenido),
    }


# ----------------------------------------------------------
# Decisión del usuario (RF_IA03)
# ----------------------------------------------------------

def _ids(valores):
    resultado = []
    for valor in valores:
        try:
            resultado.append(int(valor))
        except (TypeError, ValueError):
            continue
    return resultado


def etiquetas_elegidas(post):
    """Etiquetas marcadas en el formulario (solo las que existen)."""
    return list(Etiqueta.objects.filter(pk__in=_ids(post.getlist("etiquetas"))))


def etiquetas_actuales_ids(documento):
    return set(
        DocumentoEtiqueta.objects
        .filter(documento=documento)
        .values_list("etiqueta_id", flat=True)
    )


def hay_cambio_de_etiquetas(documento, post):
    elegidas = {e.pk for e in etiquetas_elegidas(post)}
    return elegidas != etiquetas_actuales_ids(documento)


@transaction.atomic
def guardar_decision(usuario, documento, post):
    """
    Guarda SOLO lo que el usuario confirmó:
      * Sincroniza las etiquetas elegidas con el documento.
      * Registra en SugerenciaInteligente qué se sugirió y qué decidió.
      * Deja una entrada en la auditoría.

    El nombre de cada sugerencia se toma de la base de datos, nunca del
    formulario; del formulario solo se leen identificadores.
    """
    # 1. Etiquetas confirmadas por el usuario.
    elegidas = etiquetas_elegidas(post)
    ids_elegidas = {e.pk for e in elegidas}
    actuales = etiquetas_actuales_ids(documento)

    DocumentoEtiqueta.objects.filter(
        documento=documento
    ).exclude(etiqueta_id__in=ids_elegidas).delete()

    for etiqueta in elegidas:
        if etiqueta.pk not in actuales:
            DocumentoEtiqueta.objects.create(documento=documento, etiqueta=etiqueta)

    # 2. Decisión sobre la categoría sugerida (solo si el usuario puede
    #    utilizar las funciones inteligentes).
    registros = []
    resumen = []

    if "inteligencia.utilizar" not in obtener_permisos(usuario):
        return registros

    ids_cat = _ids([post.get("sug_categoria")])
    sugerida = Categoria.objects.filter(pk__in=ids_cat).first()

    if sugerida is not None:
        if post.get("sug_descartada") == "1":
            estado = RECHAZADA
        elif documento.categoria_id == sugerida.pk:
            estado = ACEPTADA
        else:
            estado = MODIFICADA

        registros.append(SugerenciaInteligente(
            documento=documento,
            usuario=usuario,
            tipo_sugerencia=TIPO_CATEGORIA,
            valor_sugerido=sugerida.nombre,
            estado_decision=estado,
            valor_final=str(documento.categoria),
        ))
        resumen.append("categoría «%s»: %s" % (sugerida.nombre, estado))

    # 3. Decisión sobre cada etiqueta sugerida.
    csv = (post.get("sug_etiquetas") or "").split(",")
    for etiqueta in Etiqueta.objects.filter(pk__in=_ids(csv)):
        if etiqueta.pk in ids_elegidas:
            estado, final = ACEPTADA, etiqueta.nombre
        else:
            estado, final = RECHAZADA, None

        registros.append(SugerenciaInteligente(
            documento=documento,
            usuario=usuario,
            tipo_sugerencia=TIPO_ETIQUETA,
            valor_sugerido=etiqueta.nombre,
            estado_decision=estado,
            valor_final=final,
        ))
        resumen.append("etiqueta «%s»: %s" % (etiqueta.nombre, estado))

    SugerenciaInteligente.objects.bulk_create(registros)

    if registros:
        registrar_auditoria(
            usuario,
            ACCION_AUDITORIA,
            documento,
            "Decisión sobre sugerencias del asistente en «%s» (%s)."
            % (documento.titulo, "; ".join(resumen)),
        )

    return registros
