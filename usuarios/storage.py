from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from django.utils import timezone
import os

class ConstanciasStorage(S3Boto3Storage):
    """
    Almacenamiento personalizado para constancias de clientes en AWS S3
    Organiza archivos por año/mes/usuario para mejor gestión
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    region_name = settings.AWS_S3_REGION_NAME
    default_acl = 'private'  # Archivos privados por defecto
    file_overwrite = False   # No sobrescribir archivos
    custom_domain = False    # Sin dominio personalizado para mayor seguridad
    
    def __init__(self, *args, **kwargs):
        kwargs['bucket_name'] = self.bucket_name
        kwargs['default_acl'] = self.default_acl
        kwargs['file_overwrite'] = self.file_overwrite
        super().__init__(*args, **kwargs)
    
    def get_available_name(self, name, max_length=None):
        """
        Generar nombre único si el archivo ya existe
        """
        if self.exists(name):
            # Agregar timestamp para hacer único el nombre
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            name_parts = name.rsplit('.', 1)
            if len(name_parts) == 2:
                base_name, extension = name_parts
                name = f"{base_name}_{timestamp}.{extension}"
            else:
                name = f"{name}_{timestamp}"
        
        return super().get_available_name(name, max_length)

def constancia_upload_path(instance, filename):
    """
    Función para generar la ruta de subida de constancias
    Organiza: constancias/YYYY/MM/usuario_ID/transaccion_ID_filename
    """
    # Obtener fecha actual
    now = timezone.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    
    # Obtener usuario ID
    user_id = instance.usuario.id
    
    # Generar nombre seguro del archivo
    safe_filename = filename.replace(' ', '_')
    safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in '._-')
    
    # Construir ruta: constancias/2025/06/usuario_123/transaccion_456_comprobante.pdf
    return f'constancias/{year}/{month}/usuario_{user_id}/transaccion_{instance.id}_{safe_filename}'

class VerificationDocumentsStorage(S3Boto3Storage):
    """
    Almacenamiento para documentos de verificación DIDIT
    Mayor nivel de seguridad y organización
    """
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    region_name = settings.AWS_S3_REGION_NAME
    default_acl = 'private'
    file_overwrite = False
    custom_domain = False
    
    def __init__(self, *args, **kwargs):
        kwargs['bucket_name'] = self.bucket_name
        kwargs['default_acl'] = self.default_acl
        kwargs['file_overwrite'] = self.file_overwrite
        # Agregar encriptación adicional para documentos de verificación
        kwargs['object_parameters'] = {
            'ServerSideEncryption': 'AES256',
            'StorageClass': 'STANDARD_IA'  # Para documentos que se acceden menos frecuentemente
        }
        super().__init__(*args, **kwargs)

def verification_upload_path(instance, filename):
    """
    Ruta para documentos de verificación DIDIT
    verificacion/YYYY/MM/usuario_ID/didit_session_ID_filename
    """
    now = timezone.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    user_id = instance.user.id
    
    safe_filename = filename.replace(' ', '_')
    safe_filename = ''.join(c for c in safe_filename if c.isalnum() or c in '._-')
    
    session_id = instance.didit_session_id or 'no_session'
    
    return f'verificacion/{year}/{month}/usuario_{user_id}/{session_id}_{safe_filename}' 