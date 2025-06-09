from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Perfil
from .models import Transaccion
from .utils import enviar_notificacion_operacion_completada
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        # Si el usuario es creado, automáticamente creamos su perfil
        Perfil.objects.create(user=instance)

@receiver(pre_save, sender=Transaccion)
def capturar_estado_anterior(sender, instance, **kwargs):
    """
    Captura el estado anterior de la transacción antes de guardar
    """
    if instance.pk:  # Solo si la instancia ya existe (es una actualización)
        try:
            # Obtener el estado anterior desde la base de datos
            estado_anterior = Transaccion.objects.get(pk=instance.pk).estado
            # Guardar el estado anterior en la instancia para usar en post_save
            instance._estado_anterior = estado_anterior
        except Transaccion.DoesNotExist:
            # Si no existe (nueva instancia), no hay estado anterior
            instance._estado_anterior = None
    else:
        # Nueva instancia, no hay estado anterior
        instance._estado_anterior = None

@receiver(post_save, sender=Transaccion)
def enviar_notificacion_al_completar(sender, instance, created, **kwargs):
    """
    Envía notificación por correo al cliente cuando la transacción cambia a COMPLETADA
    """
    # Solo procesar si no es una nueva transacción (created=False)
    if not created and hasattr(instance, '_estado_anterior'):
        estado_anterior = instance._estado_anterior
        estado_actual = instance.estado
        
        # Verificar si cambió de cualquier estado a COMPLETADA
        if estado_anterior != 'COMPLETADA' and estado_actual == 'COMPLETADA':
            try:
                logger.info(f"Transacción {instance.id} cambió de '{estado_anterior}' a 'COMPLETADA'. Enviando notificación al cliente...")
                
                # Enviar notificación al cliente
                enviar_notificacion_operacion_completada(instance)
                
                logger.info(f"Notificación de operación completada enviada exitosamente para transacción {instance.id}")
                
            except Exception as e:
                logger.error(f"Error al enviar notificación de operación completada para transacción {instance.id}: {str(e)}")
                # No re-raise para no interrumpir el proceso de guardado
