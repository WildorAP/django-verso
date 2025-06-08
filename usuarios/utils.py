from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

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