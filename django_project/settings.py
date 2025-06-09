from dotenv import load_dotenv
from pathlib import Path


import dj_database_url 
import os
import sys


load_dotenv()

debug_env = os.getenv('DEBUG')

if os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in sys.argv:
    print(f"1. Valor inicial de DEBUG en .env: {debug_env}")
    print(f"2. Tipo de DEBUG en .env: {type(debug_env)}")

if 'RAILWAY_ENVIRONMENT' not in os.environ:
    DEBUG = True
else:
    DEBUG = str(debug_env or "False").lower() in ['true', '1', 'yes', 'y', 'on']

if os.environ.get('RUN_MAIN') == 'true' or 'runserver' not in sys.argv:
    print(f"3. Valor final de DEBUG: {DEBUG}")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-default-key")

# SECURITY WARNING: don't run with debug turned on in production!
# Print para confirmar el valor final de DEBUG





# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'storages',  # AWS S3 Storage
    'platea',
    'usuarios.apps.UsuariosConfig',
   
]

# Redirecciones de autenticación

LOGIN_REDIRECT_URL = 'usuarios:dashboard'
LOGOUT_REDIRECT_URL = 'principal'
LOGIN_URL = 'usuarios:login'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'usuarios.middlewares.VerificarInformacionFinancieraMiddleware',
    
]

if not DEBUG:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'django_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_project.wsgi.application'


#Database
#database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Lima'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field
# DONDE

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
    BASE_DIR / 'platea/static',
]

# Configuración de archivos estáticos
if DEBUG:
    # En desarrollo, usa el backend por defecto y sirve directamente desde STATICFILES_DIRS
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    # En producción, usa WhiteNoise y STATIC_ROOT
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

ALLOWED_HOSTS = ['www.versotek.io', 'versotek.io','localhost','127.0.0.1','django-verso-production.up.railway.app']

CSRF_TRUSTED_ORIGINS =['http://*','https://django-verso-production.up.railway.app',"https://www.versotek.io"]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

X_FRAME_OPTIONS = 'SAMEORIGIN'

# Configuración de correo electrónico
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_TIMEOUT = 30

# Credenciales de correo
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# Verificar que las credenciales estén configuradas
if not all([EMAIL_HOST_USER, EMAIL_HOST_PASSWORD]):
    raise ValueError("Las credenciales de correo no están configuradas correctamente en el archivo .env")

# Email del administrador para notificaciones
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", EMAIL_HOST_USER)
if not ADMIN_EMAIL:
    print("ADVERTENCIA: ADMIN_EMAIL no está configurado en el archivo .env")
    print("Se usará EMAIL_HOST_USER como email del administrador por defecto.")

# Configuración de logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'registro.log'),
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'usuarios': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Configuración de DIDIT para verificación de identidad
DIDIT_API_KEY = os.getenv("DIDIT_API_KEY")
DIDIT_BASE_URL = os.getenv("DIDIT_BASE_URL", "https://verification.didit.me")
DIDIT_WORKFLOW_ID = os.getenv("DIDIT_WORKFLOW_ID")
DIDIT_WEBHOOK_SECRET_KEY = os.getenv("DIDIT_WEBHOOK_SECRET_KEY")

# Verificar que las configuraciones de DIDIT estén disponibles
if not DIDIT_API_KEY:
    print("ADVERTENCIA: DIDIT_API_KEY no está configurado en el archivo .env")
    print("La verificación de identidad no funcionará hasta que se configure.")

if not DIDIT_WORKFLOW_ID:
    print("ADVERTENCIA: DIDIT_WORKFLOW_ID no está configurado en el archivo .env")
    print("Debes crear un workflow en DIDIT Business Console y configurar su ID.")

if not DIDIT_WEBHOOK_SECRET_KEY:
    print("ADVERTENCIA: DIDIT_WEBHOOK_SECRET_KEY no está configurado en el archivo .env")
    print("Esto es necesario para verificar webhooks de DIDIT.")

# ============================================================================
# CONFIGURACIÓN DE AWS S3
# ============================================================================

# Credenciales AWS
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'versotek-constancias')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')

# Configuración de S3
AWS_S3_FILE_OVERWRITE = False  # No sobrescribir archivos
AWS_DEFAULT_ACL = None  # Usar ACL del bucket por defecto
AWS_S3_VERIFY = True  # Verificar certificados SSL
AWS_S3_USE_SSL = True  # Usar HTTPS

# URLs y dominios
AWS_S3_CUSTOM_DOMAIN = None  # Sin CloudFront por ahora (mayor seguridad)
AWS_S3_URL_PROTOCOL = 'https:'

# Configuraciones de archivos
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',  # Cache por 24 horas
    'ServerSideEncryption': 'AES256',  # Encriptación en reposo
}

# Configuración de timeout y reintentos
AWS_S3_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100 MB
# Configuración de transferencia compatible con boto3
AWS_S3_TRANSFER_CONFIG = None  # Usar configuración por defecto

# Configuración para archivos estáticos y media
USE_S3_FOR_STATIC = os.getenv('USE_S3_FOR_STATIC', 'False').lower() == 'true'

if USE_S3_FOR_STATIC and not DEBUG:
    # Solo usar S3 para archivos estáticos en producción si está habilitado
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
    STATIC_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/static/'

# Para archivos media (constancias, etc.)
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    # Solo usar S3 si las credenciales están configuradas
    DEFAULT_FILE_STORAGE = 'usuarios.storage.ConstanciasStorage'
    MEDIA_URL = f'https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/'
    print(f"✅ AWS S3 configurado para bucket: {AWS_STORAGE_BUCKET_NAME}")
else:
    # Fallback a almacenamiento local si no hay credenciales AWS
    print("⚠️  Credenciales AWS no encontradas. Usando almacenamiento local.")
    print("   Para usar S3, configura AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY en .env")

# Verificar configuración de AWS S3
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_STORAGE_BUCKET_NAME:
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError, ClientError
        
        # Probar conexión con S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_S3_REGION_NAME
        )
        
        # Verificar si el bucket existe
        try:
            s3_client.head_bucket(Bucket=AWS_STORAGE_BUCKET_NAME)
            print(f"✅ Bucket S3 '{AWS_STORAGE_BUCKET_NAME}' está accesible")
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                print(f"❌ El bucket '{AWS_STORAGE_BUCKET_NAME}' no existe o no es accesible")
                print("🔄 Usando almacenamiento local como fallback")
                DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
                MEDIA_URL = '/media/'
            elif error_code == 403:
                print(f"❌ Sin permisos para acceder al bucket '{AWS_STORAGE_BUCKET_NAME}'")
                print("🔄 Usando almacenamiento local como fallback")
                DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
                MEDIA_URL = '/media/'
            else:
                print(f"❌ Error al acceder al bucket S3: {e}")
                print("🔄 Usando almacenamiento local como fallback")
                DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
                MEDIA_URL = '/media/'
                
    except ImportError:
        print("⚠️  boto3 no está instalado. Instala con: pip install boto3")
        DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
        MEDIA_URL = '/media/'
    except NoCredentialsError:
        print("❌ Credenciales AWS inválidas")
        print("🔄 Usando almacenamiento local como fallback")
        DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
        MEDIA_URL = '/media/'
    except Exception as e:
        print(f"❌ Error al configurar AWS S3: {e}")
        print("🔄 Usando almacenamiento local como fallback")
        DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
        MEDIA_URL = '/media/'
else:
    print("⚠️  Credenciales AWS incompletas. Usando almacenamiento local.")
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/media/'

# Configuración específica para constancias
CONSTANCIAS_STORAGE = 'usuarios.storage.ConstanciasStorage'
VERIFICATION_DOCS_STORAGE = 'usuarios.storage.VerificationDocumentsStorage'