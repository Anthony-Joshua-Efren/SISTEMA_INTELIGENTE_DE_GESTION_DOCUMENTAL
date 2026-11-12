"""Database-free test configuration; never imports production settings or .env."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "configuration-isolated-tests-only"
DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]
DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "usuarios",
    "documentos",
    "auditoria",
    "Principal",
    "organizacion_busqueda",
    "alertas_reportes",
    "asistencia_inteligente",
]
AUTH_USER_MODEL = "usuarios.Usuario"
ROOT_URLCONF = "sistema_inteligente_de_gestión_documental.urls"
LOGIN_URL = "usuarios:login"
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "Plantillas"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
STATIC_URL = "/static/"
USE_TZ = True
LANGUAGE_CODE = "es-mx"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
