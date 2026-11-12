"""Isolated tests: all database access is forbidden, persistence is mocked."""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase
from django.urls import resolve, reverse

from documentos.models import Categoria, FormatoArchivo, TipoDocumento
from .forms import CategoriaForm, FormatoArchivoForm, TipoDocumentoForm
from . import views


def usuario(*, permiso=True, administrador=True, activo=True, rol_activo=True):
    class Permisos:
        def values_list(self, *args, **kwargs):
            return ["catalogo.administrar"] if permiso else []

    return SimpleNamespace(
        is_authenticated=True, is_active=activo, rol_id=1,
        rol=SimpleNamespace(
            nombre="Administrador" if administrador else "Colaborador",
            estado=rol_activo, rolpermiso_set=Permisos(),
        ),
        username="admin", first_name="", email="", is_staff=True,
    )


class CatalogoFormTests(SimpleTestCase):
    def test_obligatorios_y_duplicados_en_todos_los_catalogos(self):
        for form_class, model in (
            (CategoriaForm, Categoria), (TipoDocumentoForm, TipoDocumento),
            (FormatoArchivoForm, FormatoArchivo),
        ):
            with self.subTest(model=model.__name__), patch.object(model.objects, "exclude") as query:
                query.return_value.values_list.return_value = ["  Finanzas  "]
                form = form_class(data={"nombre": " finanzas ", "extension": "pdf"})
                self.assertFalse(form.is_valid())
                self.assertIn("nombre", form.errors)
                self.assertFalse(form_class(data={"nombre": "   "}).is_valid())

    def test_extension_normalizada_y_duplicados_inactivos(self):
        with patch.object(FormatoArchivo.objects, "exclude") as query:
            query.return_value.values_list.side_effect = [[], [" .PDF "]]
            form = FormatoArchivoForm(data={"nombre": "Portable", "extension": ".pdf"})
            self.assertFalse(form.is_valid())
            self.assertIn("extension", form.errors)

    def test_editar_excluye_su_propio_registro_y_normaliza(self):
        instance = FormatoArchivo(pk=4, nombre="PDF", extension="pdf", estado=False)
        with patch.object(FormatoArchivo.objects, "exclude") as query:
            query.return_value.values_list.return_value = []
            form = FormatoArchivoForm(
                data={"nombre": "  PDF  ", "extension": " .PDF "}, instance=instance,
            )
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.cleaned_data["extension"], "pdf")
            self.assertEqual(form.cleaned_data["nombre"], "PDF")
            self.assertNotIn("estado", form.fields)
            self.assertEqual(form.save(commit=False).estado, False)
            query.assert_called_with(pk=4)

    def test_extension_obligatoria_y_sin_rutas(self):
        for extension in ("", "../pdf", "tar.gz", "pdf/exe", "á"):
            with self.subTest(extension=extension), patch.object(FormatoArchivo.objects, "exclude") as query:
                query.return_value.values_list.return_value = []
                form = FormatoArchivoForm(data={"nombre": "PDF", "extension": extension})
                self.assertFalse(form.is_valid())
                self.assertIn("extension", form.errors)


class ConfiguracionViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, method="get", data=None, user=None):
        request = getattr(self.factory, method)("/configuracion/", data=data or {})
        request.user = user if user is not None else usuario()
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_todas_las_vistas_exigen_administrador_activo_y_permiso(self):
        endpoints = (
            (views.inicio, {}),
            (views.catalogo, {"catalogo": "categorias"}),
            (views.formulario, {"catalogo": "categorias"}),
            (views.formulario, {"catalogo": "categorias", "pk": 1}),
            (views.estado, {"catalogo": "categorias", "pk": 1, "accion": "desactivar"}),
        )
        for view, kwargs in endpoints:
            for method in ("get", "post"):
                for user in (
                    usuario(permiso=False), usuario(administrador=False),
                    usuario(activo=False), usuario(rol_activo=False),
                    SimpleNamespace(is_authenticated=True, is_active=True, rol_id=None),
                ):
                    with self.subTest(view=view.__name__, method=method, user=user):
                        with self.assertRaises(PermissionDenied):
                            view(self.request(method, user=user), **kwargs)
            response = view(self.request(user=AnonymousUser()), **kwargs)
            self.assertEqual(response.status_code, 302)
            self.assertIn("next=", response.url)

    def test_inicio_informativo_sin_guardado_y_con_sidebar(self):
        response = views.inicio(self.request())
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for text in ("25 MB", "15 documentos", "7 días", "Solo lectura", 'id="sidebar"'):
            self.assertIn(text, html)
        self.assertNotIn("Guardar", html)
        self.assertEqual(views.inicio(self.request("post")).status_code, 405)

    def test_lista_vacia_y_url_invalida(self):
        from django.http import Http404
        with patch.object(Categoria.objects, "order_by", return_value=[]):
            response = views.catalogo(self.request(), "categorias")
        self.assertContains(response, "No hay registros")
        with self.assertRaises(Http404):
            views.catalogo(self.request(), "usuarios")

    def test_creacion_y_edicion_guardan_modelos_existentes(self):
        for model, key in ((Categoria, "categorias"), (TipoDocumento, "tipos"), (FormatoArchivo, "formatos")):
            for editing in (False, True):
                with self.subTest(model=model.__name__, editing=editing):
                    instance = model(pk=2, nombre="Previo", estado=False) if editing else None
                    with patch.object(model.objects, "exclude") as query, patch.object(model, "save") as save, patch.object(views, "get_object_or_404", return_value=instance):
                        query.return_value.values_list.return_value = []
                        response = views.formulario(
                            self.request("post", {"nombre": "Nuevo", "extension": "pdf"}),
                            key, pk=2 if editing else None,
                        )
                        self.assertEqual(response.status_code, 302)
                        self.assertEqual(response.url, reverse("configuracion:catalogo", args=[key]))
                        save.assert_called_once()
                        if editing:
                            self.assertFalse(instance.estado)

    def test_formulario_invalido_no_guarda(self):
        with patch.object(Categoria, "save") as save:
            response = views.formulario(self.request("post", {"nombre": ""}), "categorias")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "obligatorio")
        save.assert_not_called()

    def test_cambio_estado_confirma_y_post_es_explicito_e_idempotente(self):
        for model, key in ((Categoria, "categorias"), (TipoDocumento, "tipos"), (FormatoArchivo, "formatos")):
            for action, target in (("desactivar", False), ("activar", True)):
                with self.subTest(model=model.__name__, action=action):
                    instance = model(pk=2, nombre="Prueba", estado=not target)
                    with patch.object(views, "get_object_or_404", return_value=instance), patch.object(model, "save") as save:
                        response = views.estado(self.request(), key, 2, action)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(instance.estado, not target)
                        save.assert_not_called()
                        for _ in range(2):
                            response = views.estado(self.request("post"), key, 2, action)
                            self.assertEqual(response.status_code, 302)
                            self.assertEqual(instance.estado, target)
                        save.assert_called_with(update_fields=["estado"])

    def test_csrf_rechaza_post_sin_token(self):
        from django.test import Client
        response = Client(enforce_csrf_checks=True).post(
            reverse("configuracion:estado", args=["categorias", 1, "desactivar"]),
        )
        self.assertEqual(response.status_code, 403)

    def test_rutas_y_metodos_no_permitidos(self):
        from django.http import Http404
        self.assertEqual(reverse("configuracion:inicio"), "/configuracion/")
        self.assertEqual(views.catalogo(self.request("post"), "categorias").status_code, 405)
        with self.assertRaises(Http404):
            views.estado(self.request("post"), "categorias", 1, "eliminar")


class SidebarConfiguracionTests(SimpleTestCase):
    def render_sidebar(self, route, *, visible=True):
        request = RequestFactory().get(reverse(route))
        request.resolver_match = resolve(request.path)
        return render_to_string("usuarios/sidebar.html", {
            "modulos": {
                "usuarios": True, "gestion_documental": True,
                "organizacion_busqueda": True, "versiones": True,
                "revisiones": True, "inteligencia": True,
                "configuracion": visible,
            },
        }, request=request)

    def test_enlace_compartido_resuelve_desde_todos_los_modulos(self):
        from html.parser import HTMLParser

        class Enlaces(HTMLParser):
            def __init__(self):
                super().__init__()
                self.configuracion = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and attrs.get("title") == "Configuración":
                    self.configuracion.append(attrs["href"])

        for route in (
            "usuarios:inicio", "usuarios:gestion_usuarios",
            "documentos:lista_documentos", "documentos:resumen_versiones",
            "organizacion_busqueda:organizacion_busqueda",
            "alertas_reportes:panel_alertas_reportes",
            "asistencia_inteligente:panel", "configuracion:inicio",
        ):
            with self.subTest(route=route):
                parser = Enlaces()
                parser.feed(self.render_sidebar(route))
                self.assertEqual(parser.configuracion, [reverse("configuracion:inicio")])
                self.assertIs(resolve(parser.configuracion[0]).func, views.inicio)

    def test_sidebar_oculta_configuracion_sin_permiso(self):
        html = self.render_sidebar("usuarios:inicio", visible=False)
        self.assertNotIn('title="Configuración"', html)
        self.assertIn('title="Gestión documental"', html)

    def test_destino_sigue_rechazando_usuario_sin_autorizacion(self):
        destination = reverse("configuracion:inicio")
        view = resolve(destination).func
        for user in (usuario(permiso=False), usuario(administrador=False)):
            with self.subTest(user=user):
                request = RequestFactory().get(destination)
                request.user = user
                with self.assertRaises(PermissionDenied):
                    view(request)
