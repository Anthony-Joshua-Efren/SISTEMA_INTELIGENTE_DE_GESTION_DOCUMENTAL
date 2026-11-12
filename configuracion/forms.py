"""Validated editing of existing catalogs, without schema changes."""

import re

from django import forms

from documentos.models import Categoria, FormatoArchivo, TipoDocumento


def normalizar_nombre(value):
    return " ".join((value or "").split())


def normalizar_extension(value):
    return (value or "").strip().lstrip(".").lower()


class CatalogoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nombre"].required = True
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            if name == "descripcion":
                field.widget = forms.Textarea(attrs={"rows": 3, "class": "form-control"})

    def _duplicado(self, field, value, normalize):
        # Include inactive and legacy unnormalized entries; exclude only this record.
        existing = self._meta.model.objects.exclude(pk=self.instance.pk)
        return any(
            normalize(previous) == normalize(value)
            for previous in existing.values_list(field, flat=True)
        )

    def clean_nombre(self):
        value = normalizar_nombre(self.cleaned_data["nombre"])
        if not value:
            raise forms.ValidationError("El nombre es obligatorio.")
        if self._duplicado("nombre", value, lambda text: normalizar_nombre(text).casefold()):
            raise forms.ValidationError("Ya existe un registro con este nombre, incluso si está inactivo.")
        return value


class CategoriaForm(CatalogoForm):
    class Meta:
        model = Categoria
        fields = ["nombre", "descripcion"]
        labels = {"nombre": "Nombre", "descripcion": "Descripción"}


class TipoDocumentoForm(CatalogoForm):
    class Meta:
        model = TipoDocumento
        fields = ["nombre", "descripcion"]
        labels = {"nombre": "Nombre", "descripcion": "Descripción"}


class FormatoArchivoForm(CatalogoForm):
    class Meta:
        model = FormatoArchivo
        fields = ["nombre", "extension"]
        labels = {"nombre": "Nombre", "extension": "Extensión"}
        help_texts = {"extension": "Ejemplo: pdf o .pdf. Se guarda sin punto y en minúsculas."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["extension"].required = True

    def clean_extension(self):
        value = normalizar_extension(self.cleaned_data["extension"])
        if not re.fullmatch(r"[a-z0-9]{1,10}", value):
            raise forms.ValidationError("Escribe una extensión de 1 a 10 letras o números, sin rutas ni puntos intermedios.")
        if self._duplicado("extension", value, normalizar_extension):
            raise forms.ValidationError("Ya existe un formato con esta extensión, incluso si está inactivo.")
        return value
