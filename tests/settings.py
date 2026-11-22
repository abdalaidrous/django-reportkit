SECRET_KEY = "tests"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]
USE_TZ = True
LANGUAGE_CODE = "ar"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django_reportkit",
    "tests.reportapp",
]
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
ROOT_URLCONF = "tests.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request"]}}]
STORAGES = {"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}}
REPORTKIT = {"JOB_BACKEND": "django_reportkit.jobs.backends.SyncBackend"}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
