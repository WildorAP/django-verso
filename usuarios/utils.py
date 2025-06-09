from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

def enviar_correo_con_template(asunto, template_html, context, destinatario):
    """
    Función base para enviar correos con template HTML y fallback a texto plano
    """
    try:
        # Renderizar el template HTML
        html_content = render_to_string(template_html, context)
        text_content = strip_tags(html_content)  # Versión texto plano como fallback
        
        # Crear el mensaje
        msg = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[destinatario]
        )
        
        # Adjuntar versión HTML
        msg.attach_alternative(html_content, "text/html")
        
        # Enviar el correo
        msg.send(fail_silently=False)
        logger.info(f"Correo enviado exitosamente a {destinatario}")
        return True
        
    except Exception as e:
        logger.error(f"Error al enviar correo a {destinatario}: {str(e)}")
        # Re-raise la excepción para que sea manejada por la vista
        raise

def enviar_codigo_verificacion(email, codigo):
    """
    Envía el código de verificación por correo electrónico.
    """
    try:
        context = {
            'codigo': codigo
        }
        return enviar_correo_con_template(
            asunto='Código de verificación para cambio de contraseña',
            template_html='usuarios/emails/codigo_verificacion.html',
            context=context,
            destinatario=email
        )
    except Exception as e:
        logger.error(f"Error en enviar_codigo_verificacion para {email}: {str(e)}")
        raise Exception(f"Error al enviar el correo de verificación: {str(e)}")

def enviar_codigo_verificacion_registro(email, codigo, nombre):
    """
    Envía el código de verificación para registro por correo electrónico.
    """
    try:
        context = {
            'codigo': codigo,
            'nombre': nombre
        }
        return enviar_correo_con_template(
            asunto='Verifica tu correo electrónico - Verso',
            template_html='usuarios/emails/verificacion_registro.html',
            context=context,
            destinatario=email
        )
    except Exception as e:
        logger.error(f"Error en enviar_codigo_verificacion_registro para {email}: {str(e)}")
        raise Exception(f"Error al enviar el correo de verificación de registro: {str(e)}")

def enviar_notificacion_nueva_orden(transaccion, email_admin):
    """
    Envía una notificación por correo cuando se sube una nueva constancia de transacción.
    """
    try:
        context = {
            'transaccion': transaccion,
            'cliente_nombre': transaccion.usuario.get_full_name() or transaccion.usuario.username,
            'cliente_email': transaccion.usuario.email,
            'tipo_operacion': transaccion.get_tipo_operacion_display(),
            'moneda_origen': transaccion.moneda_origen,
            'cantidad_origen': transaccion.cantidad_origen,
            'moneda_destino': transaccion.moneda_destino,
            'cantidad_destino': transaccion.cantidad_destino,
            'fecha_creacion': transaccion.fecha_creacion,
            'admin_url': f'/admin/usuarios/transaccion/{transaccion.id}/change/'
        }
        return enviar_correo_con_template(
            asunto=f'Nueva Orden Pendiente #{transaccion.id} - {transaccion.usuario.username}',
            template_html='usuarios/emails/notificacion_nueva_orden.html',
            context=context,
            destinatario=email_admin
        )
    except Exception as e:
        logger.error(f"Error en enviar_notificacion_nueva_orden para transacción {transaccion.id}: {str(e)}")
        raise Exception(f"Error al enviar notificación de nueva orden: {str(e)}")

def enviar_notificacion_operacion_completada(transaccion):
    """
    Envía una notificación por correo al cliente cuando su operación ha sido completada.
    """
    try:
        # Obtener información del perfil del cliente
        perfil = getattr(transaccion.usuario, 'perfil', None)
        cliente_nombre = perfil.nombre if perfil and perfil.nombre else transaccion.usuario.get_full_name() or transaccion.usuario.username
        
        context = {
            'transaccion': transaccion,
            'cliente_nombre': cliente_nombre,
            'cliente_email': transaccion.usuario.email,
            'tipo_operacion': transaccion.get_tipo_operacion_display(),
            'moneda_origen': transaccion.moneda_origen,
            'cantidad_origen': transaccion.cantidad_origen,
            'moneda_destino': transaccion.moneda_destino,
            'cantidad_destino': transaccion.cantidad_destino,
            'fecha_creacion': transaccion.fecha_creacion,
            'fecha_completada': transaccion.fecha_actualizacion if hasattr(transaccion, 'fecha_actualizacion') else timezone.now(),
            'dashboard_url': '/usuarios/dashboard/'
        }
        return enviar_correo_con_template(
            asunto=f'✅ Operación #{transaccion.id} Completada - Verso',
            template_html='usuarios/emails/operacion_completada.html',
            context=context,
            destinatario=transaccion.usuario.email
        )
    except Exception as e:
        logger.error(f"Error en enviar_notificacion_operacion_completada para transacción {transaccion.id}: {str(e)}")
        raise Exception(f"Error al enviar notificación de operación completada: {str(e)}") 