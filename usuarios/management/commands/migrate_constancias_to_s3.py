import os
import shutil
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.files.base import ContentFile
from usuarios.models import Transaccion
from usuarios.storage import ConstanciasStorage
import boto3
from botocore.exceptions import NoCredentialsError, ClientError


class Command(BaseCommand):
    help = 'Migra archivos de constancias del almacenamiento local a AWS S3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo mostrar qué archivos se migrarían sin ejecutar la migración',
        )
        parser.add_argument(
            '--backup',
            action='store_true',
            help='Crear backup local antes de migrar',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar migración incluso si el archivo ya existe en S3',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando migración de constancias a AWS S3...')
        )

        # Verificar configuración AWS
        if not self._verify_aws_config():
            return

        # Obtener transacciones con constancias
        transacciones_con_constancias = Transaccion.objects.filter(
            constancia_archivo__isnull=False
        ).exclude(constancia_archivo='')

        total_transacciones = transacciones_con_constancias.count()
        
        if total_transacciones == 0:
            self.stdout.write(
                self.style.WARNING('📂 No se encontraron constancias para migrar')
            )
            return

        self.stdout.write(
            f'📊 Se encontraron {total_transacciones} constancias para migrar'
        )

        # Crear backup si se solicita
        if options['backup'] and not options['dry_run']:
            self._create_backup()

        # Estadísticas
        migrados = 0
        errores = 0
        ya_existen = 0

        storage = ConstanciasStorage()

        for transaccion in transacciones_con_constancias:
            try:
                resultado = self._migrate_single_file(
                    transaccion, 
                    storage, 
                    options['dry_run'], 
                    options['force']
                )
                
                if resultado == 'migrado':
                    migrados += 1
                elif resultado == 'existe':
                    ya_existen += 1
                    
            except Exception as e:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Error con transacción {transaccion.id}: {str(e)}'
                    )
                )

        # Reporte final
        self._print_final_report(migrados, ya_existen, errores, options['dry_run'])

    def _verify_aws_config(self):
        """Verificar que AWS S3 esté configurado correctamente"""
        try:
            # Verificar credenciales
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                self.stdout.write(
                    self.style.ERROR('❌ Credenciales AWS no configuradas')
                )
                return False

            # Probar conexión con S3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME
            )

            # Verificar bucket
            s3_client.head_bucket(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Conexión S3 verificada - Bucket: {settings.AWS_STORAGE_BUCKET_NAME}'
                )
            )
            return True

        except NoCredentialsError:
            self.stdout.write(
                self.style.ERROR('❌ Credenciales AWS inválidas')
            )
            return False
        except ClientError as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error S3: {e}')
            )
            return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error de configuración: {e}')
            )
            return False

    def _create_backup(self):
        """Crear backup de las constancias locales"""
        backup_dir = os.path.join(settings.BASE_DIR, 'backup_constancias')
        constancias_dir = os.path.join(settings.BASE_DIR, 'constancias')
        
        if os.path.exists(constancias_dir):
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            
            shutil.copytree(constancias_dir, backup_dir)
            self.stdout.write(
                self.style.SUCCESS(f'💾 Backup creado en: {backup_dir}')
            )

    def _migrate_single_file(self, transaccion, storage, dry_run, force):
        """Migrar un archivo individual"""
        local_path = transaccion.constancia_archivo.path
        
        if not os.path.exists(local_path):
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Archivo local no existe: {local_path} (Transacción {transaccion.id})'
                )
            )
            return 'error'

        # Generar nueva ruta S3
        from usuarios.storage import constancia_upload_path
        new_path = constancia_upload_path(transaccion, os.path.basename(local_path))

        if dry_run:
            self.stdout.write(
                f'🔍 [DRY RUN] Migraría: {local_path} → s3://{settings.AWS_STORAGE_BUCKET_NAME}/{new_path}'
            )
            return 'migrado'

        # Verificar si ya existe en S3
        if storage.exists(new_path) and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'⏭️  Ya existe en S3: {new_path} (Transacción {transaccion.id})'
                )
            )
            return 'existe'

        # Migrar archivo
        with open(local_path, 'rb') as file:
            content = ContentFile(file.read())
            content.name = os.path.basename(local_path)
            
            # Guardar en S3
            saved_path = storage.save(new_path, content)
            
            # Actualizar modelo
            transaccion.constancia_archivo.name = saved_path
            transaccion.save(update_fields=['constancia_archivo'])

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Migrado: Transacción {transaccion.id} → {saved_path}'
            )
        )
        return 'migrado'

    def _print_final_report(self, migrados, ya_existen, errores, dry_run):
        """Imprimir reporte final de la migración"""
        action = "se migrarían" if dry_run else "migrados"
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 REPORTE DE MIGRACIÓN'))
        self.stdout.write('='*50)
        self.stdout.write(f'✅ Archivos {action}: {migrados}')
        self.stdout.write(f'⏭️  Ya existían en S3: {ya_existen}')
        self.stdout.write(f'❌ Errores: {errores}')
        self.stdout.write('='*50)
        
        if not dry_run and migrados > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'🎉 Migración completada! {migrados} archivos migrados a S3'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '💡 Recuerda: Puedes eliminar los archivos locales después de verificar que todo funciona correctamente'
                )
            ) 