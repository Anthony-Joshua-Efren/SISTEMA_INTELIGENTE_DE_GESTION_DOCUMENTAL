from django.contrib.auth.models import AbstractUser
from django.db import models


class Area(models.Model):
    id_area = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'Area'
        verbose_name = 'Área'
        verbose_name_plural = 'Áreas'

    def __str__(self):
        return self.nombre or f'Área {self.id_area}'


class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'Rol'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre or f'Rol {self.id_rol}'


class Permiso(models.Model):
    id_permiso = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    codigo = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'Permiso'

    def __str__(self):
        return self.codigo or self.nombre or f'Permiso {self.id_permiso}'


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado que se mapea a la tabla 'Usuario'
    existente en Supabase. Hereda de AbstractUser para aprovechar
    todo el sistema de autenticación de Django.
    """
    # PK mapeada a la columna real en la BD
    id = models.AutoField(primary_key=True, db_column='id_usuario')

    # FKs personalizadas
    area = models.ForeignKey(
        Area, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_area', related_name='usuarios'
    )
    rol = models.ForeignKey(
        Rol, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_rol', related_name='usuarios'
    )

    # Los campos de AbstractUser (username, email, first_name, last_name,
    # password, is_active, date_joined, last_login, is_staff, is_superuser)
    # YA COINCIDEN con las columnas de la tabla, así que no hay que redefinirlos.

    class Meta:
        managed = True
        db_table = 'Usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.username


class RolPermiso(models.Model):
    id_rol_permiso = models.AutoField(primary_key=True)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, db_column='id_rol')
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE, db_column='id_permiso')

    class Meta:
        managed = True
        db_table = 'RolPermiso'
        unique_together = ('rol', 'permiso')

    def __str__(self):
        return f'{self.rol} → {self.permiso}'