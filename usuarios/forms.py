
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import Usuario, Area, Rol


class UsuarioCrearForm(forms.ModelForm):
    """
    Formulario para registrar nuevos usuarios.
    """

    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa una contraseña",
                "autocomplete": "new-password",
            }
        )
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Confirma la contraseña",
                "autocomplete": "new-password",
            }
        )
    )

    class Meta:
        model = Usuario

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "area",
            "rol",
        ]

        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "area": "Área",
            "rol": "Rol",
        }

        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "area": forms.Select(
                attrs={"class": "form-select"}
            ),
            "rol": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["area"].queryset = Area.objects.filter(
            estado=True
        ).order_by("nombre")

        self.fields["rol"].queryset = Rol.objects.filter(
            estado=True
        ).order_by("nombre")

        for campo in [
            "username",
            "first_name",
            "last_name",
            "email",
            "area",
            "rol",
        ]:
            self.fields[campo].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Este correo electrónico ya está registrado."
            )

        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                "Las contraseñas no coinciden."
            )

        return password2

    def _post_clean(self):
        super()._post_clean()

        password = self.cleaned_data.get("password1")

        if password:
            try:
                validate_password(password, self.instance)
            except ValidationError as error:
                self.add_error("password1", error)

    def save(self, commit=True):
        usuario = super().save(commit=False)

        usuario.set_password(
            self.cleaned_data["password1"]
        )

        usuario.is_active = True

        if commit:
            usuario.save()

        return usuario


class UsuarioEditarForm(forms.ModelForm):
    """
    Formulario para actualizar los datos de un usuario.
    La contraseña actual se conserva.
    """

    class Meta:
        model = Usuario

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "area",
            "rol",
        ]

        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "area": "Área",
            "rol": "Rol",
        }

        widgets = {
            "username": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "area": forms.Select(
                attrs={"class": "form-select"}
            ),
            "rol": forms.Select(
                attrs={"class": "form-select"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["area"].queryset = Area.objects.filter(
            estado=True
        ).order_by("nombre")

        self.fields["rol"].queryset = Rol.objects.filter(
            estado=True
        ).order_by("nombre")

        # Conservar el área y rol actuales aunque estén inactivos.
        if self.instance.pk:
            if self.instance.area_id:
                self.fields["area"].queryset = (
                    Area.objects.filter(estado=True)
                    | Area.objects.filter(pk=self.instance.area_id)
                ).distinct().order_by("nombre")

            if self.instance.rol_id:
                self.fields["rol"].queryset = (
                    Rol.objects.filter(estado=True)
                    | Rol.objects.filter(pk=self.instance.rol_id)
                ).distinct().order_by("nombre")

        for campo in [
            "username",
            "first_name",
            "last_name",
            "email",
            "area",
            "rol",
        ]:
            self.fields[campo].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        existe = Usuario.objects.filter(
            email__iexact=email
        ).exclude(pk=self.instance.pk).exists()

        if existe:
            raise forms.ValidationError(
                "Este correo electrónico ya está registrado."
            )

        return email
