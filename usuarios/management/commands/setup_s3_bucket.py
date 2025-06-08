import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import boto3
from botocore.exceptions import NoCredentialsError, ClientError


class Command(BaseCommand):
    help = 'Configura el bucket de S3 con las políticas de seguridad adecuadas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-bucket',
            action='store_true',
            help='Crear el bucket si no existe',
        )
        parser.add_argument(
            '--set-cors',
            action='store_true',
            help='Configurar CORS para el bucket',
        )
        parser.add_argument(
            '--set-lifecycle',
            action='store_true',
            help='Configurar políticas de ciclo de vida',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔧 Configurando bucket de AWS S3...')
        )

        # Verificar credenciales
        if not self._verify_credentials():
            return

        # Crear cliente S3
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al crear cliente S3: {e}')
            )
            return

        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        # Crear bucket si se solicita
        if options['create_bucket']:
            self._create_bucket(bucket_name)

        # Verificar que el bucket existe
        if not self._bucket_exists(bucket_name):
            self.stdout.write(
                self.style.ERROR(f'❌ El bucket {bucket_name} no existe')
            )
            return

        # Configurar políticas básicas de seguridad
        self._set_bucket_encryption(bucket_name)
        self._set_bucket_versioning(bucket_name)
        self._set_bucket_public_access_block(bucket_name)

        # Configuraciones opcionales
        if options['set_cors']:
            self._set_cors_configuration(bucket_name)

        if options['set_lifecycle']:
            self._set_lifecycle_configuration(bucket_name)

        self.stdout.write(
            self.style.SUCCESS(f'✅ Configuración del bucket {bucket_name} completada')
        )

    def _verify_credentials(self):
        """Verificar que las credenciales AWS estén configuradas"""
        if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
            self.stdout.write(
                self.style.ERROR('❌ Credenciales AWS no configuradas en .env')
            )
            return False
        return True

    def _create_bucket(self, bucket_name):
        """Crear bucket S3 si no existe"""
        try:
            if settings.AWS_S3_REGION_NAME == 'us-east-1':
                # us-east-1 no requiere LocationConstraint
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        'LocationConstraint': settings.AWS_S3_REGION_NAME
                    }
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Bucket {bucket_name} creado exitosamente')
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'BucketAlreadyExists':
                self.stdout.write(
                    self.style.WARNING(f'⚠️  El bucket {bucket_name} ya existe')
                )
            elif error_code == 'BucketAlreadyOwnedByYou':
                self.stdout.write(
                    self.style.SUCCESS(f'✅ El bucket {bucket_name} ya te pertenece')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error al crear bucket: {e}')
                )

    def _bucket_exists(self, bucket_name):
        """Verificar si el bucket existe"""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError:
            return False

    def _set_bucket_encryption(self, bucket_name):
        """Configurar encriptación del bucket"""
        try:
            encryption_configuration = {
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
            
            self.s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration=encryption_configuration
            )
            
            self.stdout.write(
                self.style.SUCCESS('🔒 Encriptación configurada (AES256)')
            )
        except ClientError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al configurar encriptación: {e}')
            )

    def _set_bucket_versioning(self, bucket_name):
        """Habilitar versionado del bucket"""
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            self.stdout.write(
                self.style.SUCCESS('📝 Versionado habilitado')
            )
        except ClientError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al habilitar versionado: {e}')
            )

    def _set_bucket_public_access_block(self, bucket_name):
        """Bloquear acceso público al bucket"""
        try:
            self.s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            self.stdout.write(
                self.style.SUCCESS('🔐 Acceso público bloqueado')
            )
        except ClientError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al bloquear acceso público: {e}')
            )

    def _set_cors_configuration(self, bucket_name):
        """Configurar CORS para el bucket"""
        try:
            cors_configuration = {
                'CORSRules': [
                    {
                        'AllowedHeaders': ['*'],
                        'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE'],
                        'AllowedOrigins': [
                            'https://versotek.io',
                            'https://www.versotek.io',
                            'https://django-verso-production.up.railway.app',
                            'http://localhost:8000',
                            'http://127.0.0.1:8000'
                        ],
                        'ExposeHeaders': ['ETag'],
                        'MaxAgeSeconds': 3000
                    }
                ]
            }
            
            self.s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration
            )
            
            self.stdout.write(
                self.style.SUCCESS('🌐 CORS configurado')
            )
        except ClientError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al configurar CORS: {e}')
            )

    def _set_lifecycle_configuration(self, bucket_name):
        """Configurar políticas de ciclo de vida"""
        try:
            lifecycle_configuration = {
                'Rules': [
                    {
                        'ID': 'ConstanciasLifecycle',
                        'Status': 'Enabled',
                        'Filter': {
                            'Prefix': 'constancias/'
                        },
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'  # Archivos poco accedidos después de 30 días
                            },
                            {
                                'Days': 365,
                                'StorageClass': 'GLACIER'  # Archive después de 1 año
                            }
                        ]
                    },
                    {
                        'ID': 'DeleteIncompleteMultipartUploads',
                        'Status': 'Enabled',
                        'Filter': {},
                        'AbortIncompleteMultipartUpload': {
                            'DaysAfterInitiation': 7
                        }
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle_configuration
            )
            
            self.stdout.write(
                self.style.SUCCESS('⏰ Ciclo de vida configurado')
            )
        except ClientError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al configurar ciclo de vida: {e}')
            ) 