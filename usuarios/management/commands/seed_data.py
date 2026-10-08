"""
NOTAAAAA
Comando para cargar los datos iniciales del sistema.

Uso:
    python manage.py seed_data
"""

from django.core.management.base import BaseCommand

from usuarios.models import Area, Rol, Permiso, RolPermiso
from documentos.models import Categoria, TipoDocumento, FormatoArchivo


class Command(BaseCommand):
    help = "Crea los datos iniciales del Sistema Inteligente de Gestión Documental"

    def handle(self, *args, **options):

        self.stdout.write(
            self.style.MIGRATE_HEADING("Creando datos iniciales del sistema...")
        )

        # =========================================================
        # ÁREAS
        # =========================================================

        areas = [
            (
                "Tecnología de la Información (TI)",
                "Gestión de sistemas, infraestructura tecnológica y soporte.",
            ),
            (
                "Recursos Humanos",
                "Gestión y administración del personal.",
            ),
            (
                "Finanzas",
                "Gestión financiera, contable y presupuestal.",
            ),
            (
                "Seguridad",
                "Gestión de seguridad y protección del hotel.",
            ),
            (
                "Ingeniería",
                "Gestión de mantenimiento, instalaciones e infraestructura.",
            ),
            (
                "Alimentos y Bebidas",
                "Gestión de restaurantes, bares, banquetes y servicios de alimentos y bebidas.",
            ),
            (
                "Recepción",
                "Atención al huésped y operación de recepción.",
            ),
            (
                "Reservaciones",
                "Gestión y seguimiento de reservaciones.",
            ),
            (
                "Ama de Llaves",
                "Gestión de habitaciones, limpieza y operación de pisos.",
            ),
            (
                "Marketing",
                "Gestión de comunicación, promoción y marketing.",
            ),
            (
                "Dirección",
                "Gestión directiva y administrativa del hotel.",
            ),
        ]

        for nombre, descripcion in areas:
            area, created = Area.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": descripcion,
                    "estado": True,
                },
            )

            if created:
                self.stdout.write(f"  Área creada: {nombre}")

        # =========================================================
        # ROLES
        # =========================================================

        roles = [
            (
                "Administrador",
                "Control total del sistema, usuarios, permisos y documentos.",
            ),
            (
                "Responsable de Área",
                "Gestiona los documentos correspondientes a su área.",
            ),
            (
                "Colaborador",
                "Puede trabajar con documentos de acuerdo con los permisos asignados.",
            ),
            (
                "Consulta",
                "Acceso de consulta y descarga a los documentos autorizados.",
            ),
        ]

        for nombre, descripcion in roles:
            rol, created = Rol.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": descripcion,
                    "estado": True,
                },
            )

            if created:
                self.stdout.write(f"  Rol creado: {nombre}")

        # =========================================================
        # PERMISOS
        # =========================================================

        permisos = [
            # -----------------------------------------------------
            # Usuarios, áreas, roles y acceso
            # -----------------------------------------------------
            (
                "Crear usuario",
                "usuario.crear",
                "Registrar nuevos usuarios en el sistema.",
            ),
            (
                "Consultar usuario",
                "usuario.consultar",
                "Consultar usuarios registrados.",
            ),
            (
                "Modificar usuario",
                "usuario.modificar",
                "Modificar información, área o rol de un usuario.",
            ),
            (
                "Desactivar usuario",
                "usuario.desactivar",
                "Desactivar el acceso de un usuario sin eliminar su historial.",
            ),
            (
                "Administrar áreas",
                "area.administrar",
                "Crear, modificar y administrar las áreas del sistema.",
            ),
            (
                "Administrar roles",
                "rol.administrar",
                "Crear, modificar y administrar los roles del sistema.",
            ),
            (
                "Administrar permisos",
                "permiso.administrar",
                "Administrar permisos y excepciones de acceso.",
            ),

            # -----------------------------------------------------
            # Gestión documental
            # -----------------------------------------------------
            (
                "Cargar documento",
                "documento.cargar",
                "Registrar y cargar nuevos documentos.",
            ),
            (
                "Consultar documento",
                "documento.consultar",
                "Consultar documentos autorizados.",
            ),
            (
                "Descargar documento",
                "documento.descargar",
                "Descargar documentos autorizados.",
            ),
            (
                "Modificar documento",
                "documento.modificar",
                "Modificar los metadatos de un documento.",
            ),
            (
                "Archivar documento",
                "documento.archivar",
                "Archivar documentos que dejan de estar vigentes.",
            ),
            (
                "Eliminar documento",
                "documento.eliminar",
                "Eliminar documentos cuando el usuario tenga autorización.",
            ),

            # -----------------------------------------------------
            # Versiones y trazabilidad
            # -----------------------------------------------------
            (
                "Crear nueva versión",
                "documento.versionar",
                "Registrar una nueva versión de un documento.",
            ),
            (
                "Consultar historial de versiones",
                "version.consultar",
                "Consultar el historial de versiones de los documentos autorizados.",
            ),
            (
                "Consultar auditoría",
                "auditoria.consultar",
                "Consultar la bitácora y trazabilidad de las acciones realizadas.",
            ),

            # -----------------------------------------------------
            # Organización, búsqueda y tipos documentales
            # -----------------------------------------------------
            (
                "Administrar catálogos",
                "catalogo.administrar",
                "Administrar categorías, etiquetas, tipos y formatos documentales.",
            ),

            # -----------------------------------------------------
            # Revisiones, alertas y reportes
            # -----------------------------------------------------
            (
                "Gestionar revisión y vencimiento",
                "revision.gestionar",
                "Registrar y modificar fechas de revisión y vencimiento de documentos.",
            ),
            (
                "Consultar alertas e indicadores",
                "alerta.consultar",
                "Consultar alertas, vencimientos e indicadores documentales autorizados.",
            ),
            (
                "Generar reportes",
                "reporte.generar",
                "Generar y consultar reportes del sistema.",
            ),

            # -----------------------------------------------------
            # Funciones inteligentes
            # -----------------------------------------------------
            (
                "Utilizar funciones inteligentes",
                "inteligencia.utilizar",
                "Utilizar sugerencias inteligentes de categorías y etiquetas.",
            ),
        ]

        for nombre, codigo, descripcion in permisos:
            permiso, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "descripcion": descripcion,
                },
            )

            if created:
                self.stdout.write(f"  Permiso creado: {codigo}")

        # =========================================================
        # PERMISOS POR ROL
        # =========================================================

        permisos_por_rol = {
            "Administrador": [
                "usuario.crear",
                "usuario.consultar",
                "usuario.modificar",
                "usuario.desactivar",
                "area.administrar",
                "rol.administrar",
                "permiso.administrar",

                "documento.cargar",
                "documento.consultar",
                "documento.descargar",
                "documento.modificar",
                "documento.archivar",
                "documento.eliminar",

                "documento.versionar",
                "version.consultar",
                "auditoria.consultar",

                "catalogo.administrar",

                "revision.gestionar",
                "alerta.consultar",
                "reporte.generar",

                "inteligencia.utilizar",
            ],

            "Responsable de Área": [
                "usuario.consultar",

                "documento.cargar",
                "documento.consultar",
                "documento.descargar",
                "documento.modificar",
                "documento.archivar",

                "documento.versionar",
                "version.consultar",
                "auditoria.consultar",

                "revision.gestionar",
                "alerta.consultar",
                "reporte.generar",

                "inteligencia.utilizar",
            ],

            "Colaborador": [
                "documento.cargar",
                "documento.consultar",
                "documento.descargar",
                "documento.modificar",

                "documento.versionar",
                "version.consultar",

                "alerta.consultar",

                "inteligencia.utilizar",
            ],

            "Consulta": [
                "documento.consultar",
                "documento.descargar",
                "version.consultar",
            ],
        }

        for nombre_rol, codigos in permisos_por_rol.items():

            rol = Rol.objects.get(nombre=nombre_rol)
            RolPermiso.objects.filter(rol=rol).exclude(
                permiso__codigo__in=codigos
            ).delete()

            for codigo in codigos:

                permiso = Permiso.objects.get(codigo=codigo)

                RolPermiso.objects.get_or_create(
                    rol=rol,
                    permiso=permiso,
                )

            self.stdout.write(
                f"  Permisos asignados a: {nombre_rol}"
            )

        # =========================================================
        # CATEGORÍAS
        # =========================================================

        categorias = [
            ("Operación", "Documentación relacionada con la operación general del hotel."),
            ("Administración", "Documentación administrativa y de gestión interna."),
            ("Finanzas", "Documentación financiera, contable y presupuestal."),
            ("Recursos Humanos", "Documentación relacionada con la gestión del personal."),
            ("Tecnología", "Documentación de sistemas, infraestructura y servicios tecnológicos."),
            ("Seguridad", "Documentación relacionada con seguridad y protección."),
            ("Mantenimiento e Ingeniería", "Documentación técnica de instalaciones, equipos y mantenimiento."),
            ("Alimentos y Bebidas", "Documentación relacionada con restaurantes, bares, banquetes y servicios de alimentos."),
            ("Comercial y Marketing", "Documentación comercial, promocional y de marketing."),
            ("Cumplimiento y Normatividad", "Documentación normativa, regulatoria y de cumplimiento."),
        ]

        for nombre, descripcion in categorias:

            categoria, created = Categoria.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": descripcion,
                    "estado": True,
                },
            )

            if created:
                self.stdout.write(
                    f"  Categoría creada: {nombre}"
                )

        # =========================================================
        # TIPOS DE DOCUMENTO
        # =========================================================

        tipos_documento = [
            ("Manual", "Documento explicativo para el uso de sistemas, equipos o procesos."),
            ("Procedimiento", "Documento que establece los pasos de una actividad o proceso."),
            ("Política", "Lineamiento o disposición interna."),
            ("Formato", "Documento estructurado para captura o registro de información."),
            ("Reporte", "Documento que presenta información, resultados o indicadores."),
            ("Contrato", "Documento que formaliza acuerdos entre las partes."),
            ("Factura", "Documento fiscal relacionado con una operación comercial."),
            ("Cotización", "Propuesta económica de productos o servicios."),
            ("Inventario", "Registro de equipos, materiales, productos o bienes."),
            ("Certificado", "Documento que acredita una condición, cumplimiento o garantía."),
            ("Acta", "Documento que registra formalmente hechos, acuerdos o reuniones."),
            ("Guía", "Documento de orientación para realizar una actividad."),
            ("Diagrama", "Representación gráfica de procesos, sistemas o infraestructura."),
        ]

        for nombre, descripcion in tipos_documento:

            tipo, created = TipoDocumento.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "descripcion": descripcion,
                    "estado": True,
                },
            )

            if created:
                self.stdout.write(
                    f"  Tipo de documento creado: {nombre}"
                )

        # =========================================================
        # FORMATOS DE ARCHIVO
        # =========================================================

        formatos = [
            ("PDF", "pdf"),
            ("Word", "docx"),
            ("Excel", "xlsx"),
            ("Excel antiguo", "xls"),
            ("PowerPoint", "pptx"),
            ("Imagen JPG", "jpg"),
            ("Imagen JPEG", "jpeg"),
            ("Imagen PNG", "png"),
            ("XML", "xml"),
            ("Texto plano", "txt"),
        ]

        for nombre, extension in formatos:

            formato, created = FormatoArchivo.objects.get_or_create(
                extension=extension,
                defaults={
                    "nombre": nombre,
                    "estado": True,
                },
            )

            if created:
                self.stdout.write(
                    f"  Formato creado: {nombre} (.{extension})"
                )

        # =========================================================
        # RESUMEN
        # =========================================================

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Datos iniciales creados correctamente."
            )
        )

        self.stdout.write(
            f"Áreas: {Area.objects.count()}"
        )

        self.stdout.write(
            f"Roles: {Rol.objects.count()}"
        )

        self.stdout.write(
            f"Permisos: {Permiso.objects.count()}"
        )

        self.stdout.write(
            f"Categorías: {Categoria.objects.count()}"
        )

        self.stdout.write(
            f"Tipos de documento: {TipoDocumento.objects.count()}"
        )

        self.stdout.write(
            f"Formatos de archivo: {FormatoArchivo.objects.count()}"
        )