from pathlib import Path

from django import forms
from django.db.models import Q

from usuarios.models import Area

from .models import Categoria, Documento, FormatoArchivo, TipoDocumento
from .permisos import es_administrador

TAMANO_MAXIMO_MB = 25


def _activos(modelo, actual_id=None):
    """Registros activos; incluye el actual aunque se haya desactivado."""
    filtro = Q(estado=True)

    if actual_id:
        filtro |= Q(pk=actual_id)

    return modelo.objects.filter(filtro).order_by("nombre")


# ==========================================================
# DATOS DEL DOCUMENTO (carga y edición)
# ==========================================================

class DocumentoForm(forms.ModelForm):

    class Meta:
        model = Documento
        fields = [
            "titulo",
            "descripcion",
            "area",
            "categoria",
            "tipo_documento",
            "fecha_documento",
            "fecha_revision",
            "fecha_vencimiento",
            "proveedor",
            "sistema_relacionado",
            "departamento",
        ]
        labels = {
            "titulo": "Título",
            "descripcion": "Descripción",
            "area": "Área",
            "categoria": "Categoría",
            "tipo_documento": "Tipo de documento",
            "fecha_documento": "Fecha del documento",
            "fecha_revision": "Fecha de revisión",
            "fecha_vencimiento": "Fecha de vencimiento",
            "proveedor": "Proveedor",
            "sistema_relacionado": "Sistema relacionado",
            "departamento": "Departamento",
        }
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_documento": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "fecha_revision": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "fecha_vencimiento": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
        }

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)

        self.usuario = usuario
        self.fields["titulo"].required = True

        actual = self.instance

        self.fields["categoria"].queryset = _activos(
            Categoria, actual.categoria_id
        )
        self.fields["tipo_documento"].queryset = _activos(
            TipoDocumento, actual.tipo_documento_id
        )

        for nombre in ("area", "categoria", "tipo_documento"):
            self.fields[nombre].empty_label = "Selecciona una opción"

        # Administrador: elige cualquier área activa.
        # Demás roles: el documento queda fijo en su propia área.
        if es_administrador(usuario):
            self.fields["area"].queryset = _activos(Area, actual.area_id)
        else:
            self.fields["area"].queryset = Area.objects.filter(
                pk=usuario.area_id
            )
            self.fields["area"].empty_label = None
            self.fields["area"].disabled = True

            if not actual.pk:
                self.initial["area"] = usuario.area_id

        # Estilos de Bootstrap
        for campo in self.fields.values():
            clase = (
                "form-select"
                if isinstance(campo.widget, forms.Select)
                else "form-control"
            )
            campo.widget.attrs["class"] = clase

    def clean(self):
        datos = super().clean()

        fecha_documento = datos.get("fecha_documento")
        fecha_revision = datos.get("fecha_revision")
        fecha_vencimiento = datos.get("fecha_vencimiento")

        if (
            fecha_documento
            and fecha_vencimiento
            and fecha_vencimiento < fecha_documento
        ):
            self.add_error(
                "fecha_vencimiento",
                "El vencimiento no puede ser anterior a la fecha del documento."
            )

        if (
            fecha_documento
            and fecha_revision
            and fecha_revision < fecha_documento
        ):
            self.add_error(
                "fecha_revision",
                "La revisión no puede ser anterior a la fecha del documento."
            )

        return datos


# ==========================================================
# CARGA: DATOS + ARCHIVO
# ==========================================================

class DocumentoCargarForm(DocumentoForm):

    archivo = forms.FileField(
        label="Archivo",
        error_messages={"required": "Selecciona el archivo del documento."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.formato = None
        self._formatos = {}

        for formato in FormatoArchivo.objects.filter(estado=True):
            extension = (formato.extension or "").strip().lstrip(".").lower()

            if extension:
                self._formatos[extension] = formato

        if self._formatos:
            permitidos = ", ".join(
                ".%s" % extension for extension in sorted(self._formatos)
            )
            self.fields["archivo"].help_text = (
                "Formatos permitidos: %s. Tamaño máximo: %s MB."
                % (permitidos, TAMANO_MAXIMO_MB)
            )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]

        if not self._formatos:
            raise forms.ValidationError(
                "No hay formatos de archivo activos configurados. "
                "Contacta al administrador."
            )

        extension = Path(archivo.name).suffix.lstrip(".").lower()

        if not extension:
            raise forms.ValidationError(
                "El archivo no tiene extensión."
            )

        formato = self._formatos.get(extension)

        if formato is None:
            permitidos = ", ".join(
                ".%s" % ext for ext in sorted(self._formatos)
            )
            raise forms.ValidationError(
                "El formato .%s no está permitido. Formatos permitidos: %s."
                % (extension, permitidos)
            )

        if archivo.size == 0:
            raise forms.ValidationError("El archivo está vacío.")

        if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
            raise forms.ValidationError(
                "El archivo supera el tamaño máximo de %s MB."
                % TAMANO_MAXIMO_MB
            )

        self.formato = formato

        return archivo
