from django.db import models


class RegistroAuditoria(models.Model):
    id_registro = models.AutoField(primary_key=True)
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.PROTECT, db_column='id_usuario', related_name='registros_auditoria')
    documento = models.ForeignKey(
        'documentos.Documento', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_documento', related_name='registros_auditoria'
    )
    accion = models.CharField(max_length=100, blank=True, null=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    resultado = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'RegistroAuditoria'
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'

    def __str__(self):
        return f'{self.usuario} - {self.accion} ({self.fecha_hora})'


class Alerta(models.Model):
    id_alerta = models.AutoField(primary_key=True)
    documento = models.ForeignKey('documentos.Documento', on_delete=models.CASCADE, db_column='id_documento', related_name='alertas')
    tipo = models.CharField(max_length=50, blank=True, null=True)
    mensaje = models.TextField(blank=True, null=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    fecha_objetivo = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = True
        db_table = 'Alerta'

    def __str__(self):
        return f'Alerta: {self.tipo} - {self.documento}'