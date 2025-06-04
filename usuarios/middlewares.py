# usuarios/middlewares.py
from django.shortcuts import redirect
from django.urls import reverse

class VerificarInformacionFinancieraMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            perfil = getattr(request.user, 'perfil', None)
            ruta_actual = request.path

            
        return self.get_response(request)
