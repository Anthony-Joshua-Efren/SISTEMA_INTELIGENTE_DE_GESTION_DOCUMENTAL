"""
Pruebas del módulo de funciones inteligentes.

  * MotorTests y ExtraccionTests no usan base de datos:
        python manage.py test asistencia_inteligente.tests.MotorTests
  * ServiciosTests y VistasTests sí crean datos (Django arma una base de
    datos de prueba), así que se recomienda correrlas con una base local:
        python manage.py test asistencia_inteligente
"""

from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

from . import catalogo, motor
from .extraccion import extraer_texto, nombre_a_texto


def _categorias():
    datos = [
        (1, "Finanzas", "Documentación financiera, contable y presupuestal."),
        (2, "Tecnología", "Documentación de sistemas, infraestructura y servicios tecnológicos."),
        (3, "Alimentos y Bebidas", "Restaurantes, bares y banquetes."),
    ]
    return [
        motor.Candidato(
            i, n, d, catalogo.PALABRAS_CLAVE_CATEGORIA.get(motor.normalizar(n), [])
        )
        for i, n, d in datos
    ]


def _etiquetas():
    return [
        motor.Candidato(
            i, n, d, catalogo.PALABRAS_CLAVE_ETIQUETA.get(motor.normalizar(n), [])
        )
        for i, (n, d) in enumerate(catalogo.ETIQUETAS_INICIALES, start=1)
    ]


class MotorTests(SimpleTestCase):

    def test_normalizar_quita_acentos_y_simbolos(self):
        self.assertEqual(motor.normalizar("Configuración_Red-PMS"), "configuracion red pms")

    def test_tokenizar_ignora_stopwords_y_singulariza(self):
        self.assertEqual(motor.tokenizar("Los servidores de la red"), ["servidor", "red"])

    def test_sugiere_tecnologia_para_manual_de_opera(self):
        s = motor.sugerir_categoria(
            _categorias(), {"titulo": "Manual de usuario Opera PMS"}
        )
        self.assertIsNotNone(s)
        self.assertEqual(s.nombre, "Tecnología")
        self.assertTrue(any("opera" in m for m in s.motivos))

    def test_sugiere_finanzas_para_factura(self):
        s = motor.sugerir_categoria(
            _categorias(), {"titulo": "Factura octubre", "tipo_documento": "Factura"}
        )
        self.assertEqual(s.nombre, "Finanzas")

    def test_no_sugiere_si_no_hay_coincidencias(self):
        self.assertIsNone(motor.sugerir_categoria(_categorias(), {"titulo": "Reporte"}))
        self.assertIsNone(motor.sugerir_categoria(_categorias(), {}))

    def test_sin_candidatos_no_falla(self):
        self.assertIsNone(motor.sugerir_categoria([], {"titulo": "Opera"}))
        self.assertEqual(motor.sugerir_etiquetas([], {"titulo": "Opera"}), [])

    def test_etiquetas_relacionadas_y_maximo(self):
        etiquetas = motor.sugerir_etiquetas(
            _etiquetas(),
            {
                "titulo": "Configuración de switches y VLAN",
                "descripcion": "Direcciones IP, respaldo y servidores de la red",
            },
        )
        nombres = [e.nombre for e in etiquetas]
        self.assertIn("Red", nombres)
        self.assertLessEqual(len(etiquetas), motor.MAXIMO_ETIQUETAS)
        # Ordenadas de mayor a menor puntaje.
        puntajes = [e.puntaje for e in etiquetas]
        self.assertEqual(puntajes, sorted(puntajes, reverse=True))

    def test_aprende_de_ejemplos_existentes(self):
        candidatos = [
            motor.Candidato(1, "Banquetes", "", [], ["boda salon jardin montaje"]),
            motor.Candidato(2, "Otros", "", [], ["varios"]),
        ]
        s = motor.sugerir_categoria(candidatos, {"titulo": "Montaje salon jardin"})
        self.assertEqual(s.nombre, "Banquetes")

    def test_puntaje_entre_0_y_1(self):
        for s in motor._puntuar(_categorias(), {"titulo": "Opera factura menu red"}):
            self.assertGreaterEqual(s.puntaje, 0)
            self.assertLessEqual(s.puntaje, 1)


class ExtraccionTests(SimpleTestCase):

    def test_nombre_a_texto(self):
        self.assertEqual(nombre_a_texto("Manual_Opera-PMS_v2.docx"), "Manual Opera PMS v2")

    def test_txt_utf8_y_cp1252(self):
        self.assertIn("configuración", extraer_texto("a.txt", "configuración".encode("utf-8")))
        self.assertIn("configuración", extraer_texto("a.txt", "configuración".encode("cp1252")))

    def test_formato_desconocido_o_dañado_devuelve_vacio(self):
        self.assertEqual(extraer_texto("a.png", b"\x89PNG"), "")
        self.assertEqual(extraer_texto("a.docx", b"no es un docx"), "")
        self.assertEqual(extraer_texto("a.txt", b""), "")

    def test_docx_real(self):
        import io
        from docx import Document

        doc = Document()
        doc.add_paragraph("Procedimiento de respaldo de servidores")
        buffer = io.BytesIO()
        doc.save(buffer)
        self.assertIn("respaldo", extraer_texto("p.docx", buffer.getvalue()))


class _Base(TestCase):
    """Datos mínimos: área, roles, permisos, categorías y etiquetas."""

    @classmethod
    def setUpTestData(cls):
        from documentos.models import Categoria, Etiqueta, TipoDocumento
        from usuarios.models import Area, Permiso, Rol, RolPermiso, Usuario

        cls.area = Area.objects.create(nombre="IT")
        cls.otra_area = Area.objects.create(nombre="Finanzas")
        cls.tipo = TipoDocumento.objects.create(nombre="Manual")
        cls.tec = Categoria.objects.create(
            nombre="Tecnología", descripcion="Sistemas e infraestructura"
        )
        cls.fin = Categoria.objects.create(nombre="Finanzas", descripcion="Contabilidad")
        cls.opera = Etiqueta.objects.create(nombre="Opera")
        cls.red = Etiqueta.objects.create(nombre="Red")
        cls.cctv = Etiqueta.objects.create(nombre="CCTV")

        def rol(nombre, codigos):
            r = Rol.objects.create(nombre=nombre)
            for codigo in codigos:
                p, _ = Permiso.objects.get_or_create(codigo=codigo, defaults={"nombre": codigo})
                RolPermiso.objects.create(rol=r, permiso=p)
            return r

        colab = rol("Colaborador", [
            "documento.cargar", "documento.consultar", "documento.modificar",
            "inteligencia.utilizar",
        ])
        sin_ia = rol("Consulta", ["documento.cargar", "documento.consultar"])

        cls.usuario = Usuario.objects.create_user("ana", password="x", area=cls.area, rol=colab)
        cls.usuario_sin_ia = Usuario.objects.create_user("beto", password="x", area=cls.area, rol=sin_ia)

    def _documento(self, **extra):
        from documentos.models import Documento

        datos = dict(
            area=self.area, categoria=self.tec, tipo_documento=self.tipo,
            titulo="Manual Opera", usuario_responsable=self.usuario,
        )
        datos.update(extra)
        return Documento.objects.create(**datos)


class ServiciosTests(_Base):

    def test_generar_sugerencias_usa_catalogo_y_bd(self):
        from . import servicios

        r = servicios.generar_sugerencias(
            self.usuario, {"titulo": "Manual de Opera PMS", "tipo_documento": str(self.tipo.pk)}
        )
        self.assertEqual(r["categoria"]["id"], self.tec.pk)
        self.assertIn(self.opera.pk, [e["id"] for e in r["etiquetas"]])

    def test_guardar_decision_acepta_y_rechaza_y_audita(self):
        from auditoria.models import RegistroAuditoria
        from documentos.models import DocumentoEtiqueta, SugerenciaInteligente

        from . import servicios

        documento = self._documento()

        class Post(dict):
            def getlist(self, k):
                v = self.get(k, [])
                return v if isinstance(v, list) else [v]

        post = Post({
            "etiquetas": [str(self.opera.pk)],           # elige Opera
            "sug_categoria": str(self.tec.pk),            # sugerida = la final
            "sug_etiquetas": "%d,%d" % (self.opera.pk, self.red.pk),
        })
        servicios.guardar_decision(self.usuario, documento, post)

        # Solo se guardó lo que el usuario eligió.
        self.assertEqual(
            list(DocumentoEtiqueta.objects.filter(documento=documento).values_list("etiqueta_id", flat=True)),
            [self.opera.pk],
        )
        estados = {
            (s.tipo_sugerencia, s.valor_sugerido): s.estado_decision
            for s in SugerenciaInteligente.objects.filter(documento=documento)
        }
        self.assertEqual(estados[("categoria", "Tecnología")], "aceptada")
        self.assertEqual(estados[("etiqueta", "Opera")], "aceptada")
        self.assertEqual(estados[("etiqueta", "Red")], "rechazada")
        self.assertTrue(
            RegistroAuditoria.objects.filter(documento=documento, accion="sugerencia.resolver").exists()
        )

    def test_categoria_modificada_y_rechazada(self):
        from documentos.models import SugerenciaInteligente

        from . import servicios

        class Post(dict):
            def getlist(self, k):
                return []

        documento = self._documento(categoria=self.fin)  # el usuario eligió otra
        servicios.guardar_decision(self.usuario, documento, Post({"sug_categoria": str(self.tec.pk)}))
        self.assertEqual(
            SugerenciaInteligente.objects.get(documento=documento).estado_decision, "modificada"
        )

        documento2 = self._documento()
        servicios.guardar_decision(
            self.usuario, documento2, Post({"sug_categoria": str(self.tec.pk), "sug_descartada": "1"})
        )
        self.assertEqual(
            SugerenciaInteligente.objects.get(documento=documento2).estado_decision, "rechazada"
        )

    def test_sin_permiso_no_se_registran_decisiones(self):
        from documentos.models import SugerenciaInteligente

        from . import servicios

        class Post(dict):
            def getlist(self, k):
                return []

        documento = self._documento(usuario_responsable=self.usuario_sin_ia)
        servicios.guardar_decision(
            self.usuario_sin_ia, documento, Post({"sug_categoria": str(self.tec.pk)})
        )
        self.assertFalse(SugerenciaInteligente.objects.filter(documento=documento).exists())

    def test_etiquetas_se_sincronizan_al_editar(self):
        from documentos.models import DocumentoEtiqueta

        from . import servicios

        class Post(dict):
            def getlist(self, k):
                v = self.get(k, [])
                return v if isinstance(v, list) else [v]

        documento = self._documento()
        DocumentoEtiqueta.objects.create(documento=documento, etiqueta=self.cctv)
        post = Post({"etiquetas": [str(self.red.pk)]})
        self.assertTrue(servicios.hay_cambio_de_etiquetas(documento, post))

        servicios.guardar_decision(self.usuario, documento, post)
        self.assertEqual(servicios.etiquetas_actuales_ids(documento), {self.red.pk})
        self.assertFalse(servicios.hay_cambio_de_etiquetas(documento, post))


class VistasTests(_Base):

    def test_sugerir_requiere_login(self):
        r = Client().post(reverse("asistencia_inteligente:sugerir"), {"titulo": "Opera"})
        self.assertEqual(r.status_code, 302)

    def test_sugerir_devuelve_json(self):
        c = Client()
        c.force_login(self.usuario)
        r = c.post(reverse("asistencia_inteligente:sugerir"), {"titulo": "Manual de Opera PMS"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["categoria"]["nombre"], "Tecnología")

    def test_sugerir_sin_datos_pide_captura(self):
        c = Client()
        c.force_login(self.usuario)
        r = c.post(reverse("asistencia_inteligente:sugerir"), {})
        self.assertIn("mensaje", r.json())

    def test_sugerir_sin_permiso_inteligencia_es_403(self):
        c = Client()
        c.force_login(self.usuario_sin_ia)
        r = c.post(reverse("asistencia_inteligente:sugerir"), {"titulo": "Opera"})
        self.assertEqual(r.status_code, 403)

    def test_sugerir_solo_acepta_post(self):
        c = Client()
        c.force_login(self.usuario)
        self.assertEqual(c.get(reverse("asistencia_inteligente:sugerir")).status_code, 405)

    def test_panel_requiere_permiso(self):
        c = Client()
        c.force_login(self.usuario_sin_ia)
        self.assertEqual(c.get(reverse("asistencia_inteligente:panel")).status_code, 403)
        c.force_login(self.usuario)
        self.assertEqual(c.get(reverse("asistencia_inteligente:panel")).status_code, 200)


class IntegracionDocumentosTests(_Base):
    """Carga y edición reales de documentos con el panel del asistente."""

    def setUp(self):
        from documentos.models import FormatoArchivo

        FormatoArchivo.objects.create(nombre="Texto plano", extension="txt")
        self.client = Client()
        self.client.force_login(self.usuario)

    def _datos_carga(self, **extra):
        from django.core.files.uploadedfile import SimpleUploadedFile

        datos = {
            "titulo": "Manual Opera PMS",
            "area": self.area.pk,
            "categoria": self.tec.pk,
            "tipo_documento": self.tipo.pk,
            "archivo": SimpleUploadedFile("manual_opera.txt", b"contenido de prueba"),
        }
        datos.update(extra)
        return datos

    def test_formulario_muestra_el_panel(self):
        r = self.client.get(reverse("documentos:cargar_documento"))
        self.assertContains(r, "Asistente inteligente")
        self.assertContains(r, 'name="etiquetas"')

    def test_formulario_sin_permiso_no_muestra_asistente_pero_si_etiquetas(self):
        self.client.force_login(self.usuario_sin_ia)
        r = self.client.get(reverse("documentos:cargar_documento"))
        self.assertNotContains(r, "Asistente inteligente")
        self.assertContains(r, 'name="etiquetas"')

    def test_cargar_guarda_solo_etiquetas_confirmadas(self):
        from unittest import mock

        from documentos.models import Documento, DocumentoEtiqueta, SugerenciaInteligente

        datos = self._datos_carga(**{
            "etiquetas": [self.opera.pk],
            "sug_categoria": self.tec.pk,
            "sug_etiquetas": "%d,%d" % (self.opera.pk, self.red.pk),
        })
        with mock.patch("documentos.views.guardar_archivo", return_value="1/v1_x.txt"):
            r = self.client.post(reverse("documentos:cargar_documento"), datos)

        self.assertEqual(r.status_code, 302)
        documento = Documento.objects.get(titulo="Manual Opera PMS")
        self.assertEqual(
            list(DocumentoEtiqueta.objects.filter(documento=documento).values_list("etiqueta__nombre", flat=True)),
            ["Opera"],
        )
        self.assertEqual(SugerenciaInteligente.objects.filter(documento=documento).count(), 3)

    def test_cargar_sin_usar_el_asistente_funciona_igual(self):
        from unittest import mock

        from documentos.models import Documento, DocumentoEtiqueta

        with mock.patch("documentos.views.guardar_archivo", return_value="1/v1_x.txt"):
            r = self.client.post(reverse("documentos:cargar_documento"), self._datos_carga())

        self.assertEqual(r.status_code, 302)
        self.assertFalse(DocumentoEtiqueta.objects.filter(
            documento=Documento.objects.get(titulo="Manual Opera PMS")
        ).exists())

    def test_editar_solo_etiquetas_no_dice_sin_cambios(self):
        from documentos.models import DocumentoEtiqueta

        documento = self._documento()
        datos = {
            "titulo": documento.titulo,
            "area": self.area.pk,
            "categoria": self.tec.pk,
            "tipo_documento": self.tipo.pk,
            "etiquetas": [self.red.pk],
        }
        r = self.client.post(reverse("documentos:editar_documento", args=[documento.pk]), datos)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(
            list(DocumentoEtiqueta.objects.filter(documento=documento).values_list("etiqueta_id", flat=True)),
            [self.red.pk],
        )

    def test_detalle_muestra_etiquetas(self):
        from documentos.models import DocumentoEtiqueta

        documento = self._documento()
        DocumentoEtiqueta.objects.create(documento=documento, etiqueta=self.opera)
        r = self.client.get(reverse("documentos:detalle_documento", args=[documento.pk]))
        self.assertContains(r, "Opera")
