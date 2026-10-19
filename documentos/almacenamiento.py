
import io
import mimetypes
import os
import uuid
from functools import lru_cache
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


@lru_cache(maxsize=1)
def _bucket():
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    clave = os.environ.get("SUPABASE_SECRET_KEY")

    if not url or not clave:
        raise ImproperlyConfigured(
            "Faltan SUPABASE_URL y SUPABASE_SECRET_KEY en el archivo .env."
        )

    nombre = os.environ.get("SUPABASE_BUCKET", "documentos")

    return create_client(url, clave).storage.from_(nombre)


def guardar_archivo(archivo, documento_id, numero_version):
    """Sube el archivo al bucket y devuelve su ruta."""
    extension = Path(archivo.name).suffix.lower()
    ruta = f"{documento_id}/v{numero_version}_{uuid.uuid4().hex}{extension}"

    tipo = mimetypes.guess_type(archivo.name)[0] or "application/octet-stream"

    archivo.seek(0)
    _bucket().upload(ruta, archivo.read(), {"content-type": tipo})

    return ruta


def abrir_archivo(ruta):
    """
    Descarga el archivo del bucket y lo devuelve como objeto de archivo.

    Si no se puede obtener, lanza FileNotFoundError, que la vista de
    descarga ya maneja con un mensaje y un registro de auditoría.
    """
    try:
        contenido = _bucket().download(ruta)
    except Exception as error:
        raise FileNotFoundError(
            "No se pudo descargar «%s» de Supabase Storage." % ruta
        ) from error

    return io.BytesIO(contenido)


def eliminar_archivo(ruta):
    """Elimina el archivo del bucket; no falla si ya no existe."""
    try:
        _bucket().remove([ruta])
    except Exception:
        pass
