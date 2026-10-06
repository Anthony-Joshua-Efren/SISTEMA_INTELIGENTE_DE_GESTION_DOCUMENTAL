from django.db import models


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'Categoria'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre or f'Categoría {self.id_categoria}'


class Etiqueta(models.Model):
    id_etiqueta = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'Etiqueta'

    def __str__(self):
        return self.nombre or f'Etiqueta {self.id_etiqueta}'


class TipoDocumento(models.Model):
    id_tipo_documento = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'TipoDocumento'
        verbose_name = 'Tipo de Documento'
        verbose_name_plural = 'Tipos de Documento'

    def __str__(self):
        return self.nombre or f'Tipo {self.id_tipo_documento}'


class FormatoArchivo(models.Model):
    id_formato = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, blank=True, null=True)
    extension = models.CharField(max_length=10, blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'FormatoArchivo'
        verbose_name = 'Formato de Archivo'
        verbose_name_plural = 'Formatos de Archivo'

    def __str__(self):
        return f'{self.nombre} (.{self.extension})' if self.extension else (self.nombre or f'Formato {self.id_formato}')


class Documento(models.Model):
    id_documento = models.AutoField(primary_key=True)
    area = models.ForeignKey(
        'usuarios.Area', on_delete=models.PROTECT,
        db_column='id_area', related_name='documentos'
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT,
        db_column='id_categoria', related_name='documentos'
    )
    tipo_documento = models.ForeignKey(
        TipoDocumento, on_delete=models.PROTECT,
        db_column='id_tipo_documento', related_name='documentos'
    )
    usuario_responsable = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_usuario_responsable', related_name='documentos_responsable'
    )
    titulo = models.CharField(max_length=255, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha_carga = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    fecha_documento = models.DateField(blank=True, null=True)
    fecha_revision = models.DateField(blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    proveedor = models.CharField(max_length=150, blank=True, null=True)
    sistema_relacionado = models.CharField(max_length=100, blank=True, null=True)
    departamento = models.CharField(max_length=100, blank=True, null=True)
    estado = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'Documento'

    def __str__(self):
        return self.titulo or f'Documento {self.id_documento}'


class DocumentoEtiqueta(models.Model):
    id_documento_etiqueta = models.AutoField(primary_key=True)
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, db_column='id_documento')
    etiqueta = models.ForeignKey(Etiqueta, on_delete=models.CASCADE, db_column='id_etiqueta')

    class Meta:
        managed = True
        db_table = 'DocumentoEtiqueta'
        unique_together = ('documento', 'etiqueta')


class VersionDocumento(models.Model):
    id_version = models.AutoField(primary_key=True)
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, db_column='id_documento', related_name='versiones')
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.PROTECT, db_column='id_usuario')
    formato = models.ForeignKey(FormatoArchivo, on_delete=models.PROTECT, db_column='id_formato')
    numero_version = models.IntegerField(blank=True, null=True)
    archivo = models.CharField(max_length=500, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    comentario_cambio = models.TextField(blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'VersionDocumento'

    def __str__(self):
        return f'{self.documento} - v{self.numero_version}'


class PermisoDocumento(models.Model):
    id_permiso_documento = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, db_column='id_usuario')
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, db_column='id_documento')
    permiso = models.ForeignKey('usuarios.Permiso', on_delete=models.CASCADE, db_column='id_permiso')
    tipo_acceso = models.CharField(max_length=50, blank=True, null=True)
    permitido = models.BooleanField(default=True)

    class Meta:
        managed = True
        db_table = 'PermisoDocumento'


class SugerenciaInteligente(models.Model):
    id_sugerencia = models.AutoField(primary_key=True)
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, db_column='id_documento')
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, db_column='id_usuario')
    tipo_sugerencia = models.CharField(max_length=50, blank=True, null=True)
    valor_sugerido = models.CharField(max_length=255, blank=True, null=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    estado_decision = models.CharField(max_length=50, blank=True, null=True)
    valor_final = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'SugerenciaInteligente'