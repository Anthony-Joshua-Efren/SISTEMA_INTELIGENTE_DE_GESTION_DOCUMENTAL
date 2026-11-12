"""
Extracción de texto de los archivos para apoyar las sugerencias.

El texto solo se usa en memoria para calcular la sugerencia; no se guarda.
Si el formato no se puede leer, se devuelve cadena vacía y el asistente
trabaja únicamente con los datos capturados en el formulario.
"""

import io
import re
from pathlib import Path

MAXIMO_CARACTERES = 20000
MAXIMO_BYTES = 10 * 1024 * 1024  # archivos más grandes no se analizan
MAXIMO_FILAS_EXCEL = 300


def nombre_a_texto(nombre_archivo):
    """'Manual_Opera-PMS_v2.docx' -> 'Manual Opera PMS v2'."""
    base = Path(nombre_archivo or "").stem
    return re.sub(r"[_\-.]+", " ", base)


def _txt(contenido):
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return contenido.decode("utf-8", errors="ignore")


def _xml(contenido):
    return re.sub(r"<[^>]+>", " ", _txt(contenido))


def _docx(contenido):
    from docx import Document

    documento = Document(io.BytesIO(contenido))
    partes = [p.text for p in documento.paragraphs if p.text.strip()]

    for tabla in documento.tables:
        for fila in tabla.rows:
            partes.extend(c.text for c in fila.cells if c.text.strip())

    return "\n".join(partes)


def _xlsx(contenido):
    from openpyxl import load_workbook

    libro = load_workbook(io.BytesIO(contenido), read_only=True, data_only=True)
    partes = []

    for hoja in libro.worksheets:
        partes.append(hoja.title)
        for fila in hoja.iter_rows(max_row=MAXIMO_FILAS_EXCEL, values_only=True):
            partes.extend(str(v) for v in fila if v not in (None, ""))

    libro.close()
    return "\n".join(partes)


def _pptx(contenido):
    from pptx import Presentation

    presentacion = Presentation(io.BytesIO(contenido))
    partes = []

    for diapositiva in presentacion.slides:
        for forma in diapositiva.shapes:
            if getattr(forma, "has_text_frame", False):
                partes.append(forma.text_frame.text)

    return "\n".join(partes)


def _pdf(contenido):
    # pypdf es opcional: si no está instalado, el PDF se analiza solo
    # por su nombre y por los datos del formulario.
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(contenido))
    partes = []

    for pagina in lector.pages[:15]:
        partes.append(pagina.extract_text() or "")

    return "\n".join(partes)


LECTORES = {
    ".txt": _txt,
    ".csv": _txt,
    ".xml": _xml,
    ".docx": _docx,
    ".xlsx": _xlsx,
    ".pptx": _pptx,
    ".pdf": _pdf,
}


def extraer_texto(nombre_archivo, contenido):
    """Texto del archivo (recortado) o cadena vacía si no se puede leer."""
    if not contenido or len(contenido) > MAXIMO_BYTES:
        return ""

    lector = LECTORES.get(Path(nombre_archivo or "").suffix.lower())

    if lector is None:
        return ""

    try:
        return lector(contenido)[:MAXIMO_CARACTERES]
    except Exception:
        # Archivo dañado, protegido o librería no instalada.
        return ""
