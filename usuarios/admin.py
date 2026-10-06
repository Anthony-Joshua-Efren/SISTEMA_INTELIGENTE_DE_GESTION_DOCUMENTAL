from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Area, Rol, Permiso, Usuario, RolPermiso


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('id_area', 'nombre', 'estado')
    search_fields = ('nombre',)
    list_filter = ('estado',)


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id_rol', 'nombre', 'estado')
    list_filter = ('estado',)


@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ('id_permiso', 'nombre', 'codigo')


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'area', 'rol', 'is_active', 'is_staff')
    list_filter = ('area', 'rol', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ('Información organizacional', {'fields': ('area', 'rol')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información organizacional', {'fields': ('area', 'rol')}),
    )


@admin.register(RolPermiso)
class RolPermisoAdmin(admin.ModelAdmin):
    list_display = ('id_rol_permiso', 'rol', 'permiso')
    list_filter = ('rol',)