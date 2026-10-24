import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DJANGO_DEBUG', '0') == '1'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if len(SECRET_KEY) < 32:
    raise ImproperlyConfigured('Set DJANGO_SECRET_KEY to a random value of at least 32 characters.')
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
CSRF_TRUSTED_ORIGINS = [v for v in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if v]
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'core', 'catalog', 'work']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'core.middleware.SessionPolicyMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates', 'DIRS':[BASE_DIR/'templates'], 'APP_DIRS':True, 'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','core.permissions.navigation']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE':'django.db.backends.postgresql', 'NAME':os.getenv('POSTGRES_DB','papradit'), 'USER':os.getenv('POSTGRES_USER','papradit'), 'PASSWORD':os.environ.get('POSTGRES_PASSWORD',''), 'HOST':os.getenv('POSTGRES_HOST','127.0.0.1'), 'PORT':os.getenv('POSTGRES_PORT','5432'), 'CONN_MAX_AGE':60, 'OPTIONS':{'sslmode':os.getenv('POSTGRES_SSLMODE','prefer')}}}
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'th'
TIME_ZONE = 'Asia/Bangkok'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR/'staticfiles'
STATICFILES_DIRS = [BASE_DIR/'static']
STORAGES = {'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 8*60*60
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
SECURE_SSL_REDIRECT = not DEBUG
SECURE_REDIRECT_EXEMPT = [r'^health/$']
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
# Enable only behind a load balancer which strips incoming forwarding headers.
if os.getenv('TRUST_HTTPS_PROXY') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO','https')
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND','django.core.mail.backends.smtp.EmailBackend')
EMAIL_FILE_PATH = '/tmp/papradit-mail'
EMAIL_HOST = os.getenv('EMAIL_HOST','localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT','587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS','1') == '1'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD','')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL','noreply@localhost')
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL','http://localhost:8000').rstrip('/')
PASSWORD_RESET_TIMEOUT = 3600
LOGGING = {'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},'root':{'handlers':['console'],'level':'INFO'}}
