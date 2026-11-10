"""
Motor de sugerencias (RF_IA01 y RF_IA02).

Es Python puro: no usa la base de datos, ni Django, ni servicios externos.
Todo el análisis se hace en el servidor del sistema, de modo que el
contenido de los documentos (configuraciones, IPs, contratos) nunca sale
de la infraestructura del hotel.

Cómo decide
-----------
Para cada categoría (o etiqueta) candidata se arma un "perfil" de texto con
su nombre, su descripción, sus palabras clave y ejemplos de documentos que
ya tiene asignados. Luego se calcula, contra el texto del documento nuevo:

  1. Reglas: cuántas palabras clave del candidato aparecen en el documento.
  2. Similitud TF-IDF (coseno) entre el documento y el perfil.

Puntaje final = 50 % reglas + 50 % similitud, entre 0 y 1. Si ningún
candidato supera el umbral, no se sugiere nada y el usuario clasifica a
mano. El motor solo propone: nunca guarda nada.
"""

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

UMBRAL_CATEGORIA = 0.25
UMBRAL_ETIQUETA = 0.30
MAXIMO_ETIQUETAS = 5

# Con 2 palabras clave encontradas, la parte de reglas llega al máximo.
COINCIDENCIAS_PARA_MAXIMO = 2
# Similitud de coseno a partir de la cual la parte de similitud es total.
COSENO_PARA_MAXIMO = 0.35

PESO_NOMBRE_PERFIL = 3
PESO_CLAVE_PERFIL = 3

PESOS_CAMPOS = {
    "titulo": 3,
    "descripcion": 2,
    "proveedor": 2,
    "sistema_relacionado": 3,
    "departamento": 2,
    "tipo_documento": 2,
    "nombre_archivo": 2,
    "contenido": 1,
}

STOPWORDS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o",
    "u", "e", "en", "por", "para", "con", "sin", "del", "al", "a", "que",
    "se", "su", "sus", "es", "son", "como", "mas", "pero", "este", "esta",
    "estos", "estas", "ese", "esa", "lo", "le", "les", "ha", "han", "fue",
    "sobre", "entre", "desde", "hasta", "sus", "nos", "ser", "hay", "cada",
    "documento", "documentos", "archivo", "version", "final", "copia",
    "docx", "pdf", "xlsx", "pptx", "txt", "the", "and",
}


# ----------------------------------------------------------
# Texto
# ----------------------------------------------------------

def normalizar(texto):
    """Minúsculas, sin acentos y con símbolos convertidos en espacios."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]+", " ", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


def _raiz(palabra):
    """Singular aproximado, para que 'servidores' coincida con 'servidor'."""
    if len(palabra) > 5 and palabra.endswith("es"):
        return palabra[:-2]
    if len(palabra) > 4 and palabra.endswith("s"):
        return palabra[:-1]
    return palabra


def tokenizar(texto):
    tokens = []

    for palabra in normalizar(texto).split():
        if palabra in STOPWORDS or palabra.isdigit():
            continue
        # Se conservan tokens cortos como "ip", "pms" o "nom".
        if len(palabra) < 2:
            continue
        tokens.append(_raiz(palabra))

    return tokens


def _contiene_frase(texto_normalizado, frase):
    """True si la palabra o frase aparece completa (no como parte de otra)."""
    frase = normalizar(frase)
    if not frase:
        return False
    return (" %s " % frase) in (" %s " % texto_normalizado)


# ----------------------------------------------------------
# Estructuras
# ----------------------------------------------------------

@dataclass
class Candidato:
    id: int
    nombre: str
    descripcion: str = ""
    palabras_clave: list = field(default_factory=list)
    ejemplos: list = field(default_factory=list)  # textos de documentos


@dataclass
class Sugerido:
    id: int
    nombre: str
    puntaje: float
    motivos: list

    def como_diccionario(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "puntaje": round(self.puntaje, 2),
            "porcentaje": int(round(self.puntaje * 100)),
            "motivos": self.motivos,
        }


# ----------------------------------------------------------
# Vectores TF-IDF
# ----------------------------------------------------------

def _frecuencias_documento(campos):
    """Cuenta términos del documento aplicando el peso de cada campo."""
    cuenta = Counter()

    for nombre_campo, texto in campos.items():
        peso = PESOS_CAMPOS.get(nombre_campo, 1)
        for token in tokenizar(texto):
            cuenta[token] += peso

    return cuenta


def _frecuencias_perfil(candidato):
    cuenta = Counter()

    for token in tokenizar(candidato.nombre):
        cuenta[token] += PESO_NOMBRE_PERFIL
    for clave in candidato.palabras_clave:
        for token in tokenizar(clave):
            cuenta[token] += PESO_CLAVE_PERFIL
    for token in tokenizar(candidato.descripcion):
        cuenta[token] += 1
    for ejemplo in candidato.ejemplos:
        for token in tokenizar(ejemplo):
            cuenta[token] += 1

    return cuenta


def _idf(perfiles):
    total = len(perfiles)
    documentos_con = Counter()

    for perfil in perfiles:
        for termino in perfil:
            documentos_con[termino] += 1

    return {
        termino: math.log((total + 1) / (cantidad + 1)) + 1
        for termino, cantidad in documentos_con.items()
    }


def _vector(cuenta, idf):
    vector = {}

    for termino, frecuencia in cuenta.items():
        if termino in idf:
            vector[termino] = (1 + math.log(frecuencia)) * idf[termino]

    return vector


def _coseno(a, b):
    if not a or not b:
        return 0.0

    producto = sum(valor * b.get(t, 0.0) for t, valor in a.items())
    norma_a = math.sqrt(sum(v * v for v in a.values()))
    norma_b = math.sqrt(sum(v * v for v in b.values()))

    if norma_a == 0 or norma_b == 0:
        return 0.0

    return producto / (norma_a * norma_b)


# ----------------------------------------------------------
# Puntaje
# ----------------------------------------------------------

def _puntuar(candidatos, campos):
    """Devuelve lista de Sugerido ordenada de mayor a menor puntaje."""
    if not candidatos:
        return []

    texto_completo = normalizar(" ".join(campos.values()))
    if not texto_completo:
        return []

    perfiles = [_frecuencias_perfil(c) for c in candidatos]
    idf = _idf(perfiles)
    vector_doc = _vector(_frecuencias_documento(campos), idf)

    resultados = []

    for candidato, perfil in zip(candidatos, perfiles):
        # 1. Reglas: palabras clave y nombre presentes en el documento.
        claves = list(candidato.palabras_clave) + [candidato.nombre]
        encontradas = []
        for clave in claves:
            if _contiene_frase(texto_completo, clave) and clave not in encontradas:
                encontradas.append(clave)

        reglas = min(1.0, len(encontradas) / COINCIDENCIAS_PARA_MAXIMO)

        # 2. Similitud de texto.
        coseno = _coseno(vector_doc, _vector(perfil, idf))
        similitud = min(1.0, coseno / COSENO_PARA_MAXIMO)

        puntaje = 0.5 * reglas + 0.5 * similitud

        motivos = []
        if encontradas:
            motivos.append("Coincide con: %s" % ", ".join(encontradas[:4]))
        if coseno >= 0.10:
            motivos.append("Texto parecido a documentos de este grupo")

        resultados.append(
            Sugerido(candidato.id, candidato.nombre, puntaje, motivos)
        )

    resultados.sort(key=lambda s: (-s.puntaje, s.nombre))
    return resultados


# ----------------------------------------------------------
# API pública
# ----------------------------------------------------------

def sugerir_categoria(candidatos, campos, umbral=UMBRAL_CATEGORIA):
    """Mejor categoría o None si ninguna supera el umbral."""
    resultados = _puntuar(candidatos, campos)

    if resultados and resultados[0].puntaje >= umbral:
        return resultados[0]

    return None


def sugerir_etiquetas(candidatos, campos, umbral=UMBRAL_ETIQUETA,
                      maximo=MAXIMO_ETIQUETAS):
    """Hasta `maximo` etiquetas que superan el umbral."""
    resultados = _puntuar(candidatos, campos)
    return [s for s in resultados if s.puntaje >= umbral][:maximo]
