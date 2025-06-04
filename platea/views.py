from django.shortcuts import render
from platea.models import ExchangeRate
import json

# Create your views here.

from django.http import JsonResponse

def get_exchange_rate(request):
    rates = ExchangeRate.objects.all()
    data = {
        "rates": [
            {
                "currency_from": rate.currency_from,
                "currency_to": rate.currency_to,
                "rate_compra": float(rate.rate_compra),
                "rate_venta": float(rate.rate_venta)
            }
            for rate in rates
        ]
    }
    return JsonResponse(data)

def render_index(request):
    tasas_cambio = ExchangeRate.objects.all()
    tasas_dict = {
        f"{t.currency_from}_{t.currency_to}": {
            "compra": float(t.rate_compra),
            "venta": float(t.rate_venta),
        }
        for t in tasas_cambio
    }
    
    return render(request, 'index.html', {
        'tasas': tasas_dict,
        'tasas_json': json.dumps(tasas_dict)
    })

def academy(request):
    return render(request, "academy.html")  # Nueva plantilla Academy

def empresas_view(request):
    return render(request, 'empresas.html')