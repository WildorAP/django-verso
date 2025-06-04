from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

def enviar_codigo_verificacion(email, codigo):
    """
    Envía el código de verificación por correo electrónico.
    """
    asunto = 'Código de verificación para cambio de contraseña'
    mensaje = f"""
    Has solicitado cambiar tu contraseña.
    
    Tu código de verificación es: {codigo}
    
    Este código expirará en 15 minutos.
    
    Si no has solicitado este cambio, por favor ignora este mensaje.
    """
    
    try:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        raise Exception(f"Error al enviar el correo: {str(e)}")

def enviar_codigo_verificacion_registro(email, codigo, nombre):
    """
    Envía el código de verificación para registro por correo electrónico.
    """
    asunto = 'Verifica tu correo electrónico'
    mensaje = f"""
    ¡Hola {nombre}!
    
    Gracias por registrarte. Para completar tu registro, por favor ingresa el siguiente código:
    
    {codigo}
    
    Este código expirará en 24 horas.
    
    Si no has creado una cuenta, por favor ignora este mensaje.
    """
    
    try:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        raise Exception(f"Error al enviar el correo: {str(e)}") 