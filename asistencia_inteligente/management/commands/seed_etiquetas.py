from django.core.management.base import BaseCommand

from asistencia_inteligente.catalogo import ETIQUETAS_INICIALES
from documentos.models import Etiqueta


class Command(BaseCommand):
    help = "Crea las etiquetas iniciales del hotel (no duplica las existentes)."

    def handle(self, *args, **options):
        creadas = 0

        for nombre, descripcion in ETIQUETAS_INICIALES:
            _, nueva = Etiqueta.objects.get_or_create(
                nombre=nombre, defaults={"descripcion": descripcion}
            )
            creadas += int(nueva)

        self.stdout.write(self.style.SUCCESS(
            "Etiquetas creadas: %d (total: %d)."
            % (creadas, Etiqueta.objects.count())
        ))
