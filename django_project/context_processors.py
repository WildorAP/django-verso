from django.conf import settings

def google_analytics(request):
    """
    Context processor para Google Analytics
    Hace disponibles las configuraciones de Google Analytics en todos los templates
    """
    return {
        'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID,
        'GOOGLE_ANALYTICS_ENABLED': settings.GOOGLE_ANALYTICS_ENABLED,
    } 