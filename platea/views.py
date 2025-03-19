from django.shortcuts import render

# Create your views here.

from django.http import JsonResponse
from .models import ExchangeRate

def get_exchange_rate(request):
    rates = ExchangeRate.objects.all()
    data = {
        "rates": [
            {
                "currency_from": rate.currency_from,
                "currency_to": rate.currency_to,
                "rate": float(rate.rate)
            }
            for rate in rates
        ]
    }
    return JsonResponse(data)

def render_index(request):
    return render(request, 'index.html')

def academy(request):
    return render(request, "academy.html")  # Nueva plantilla Academy

def empresas_view(request):
    return render(request, 'empresas.html')