from django.contrib import admin

# Register your models here.
from .models import ExchangeRate

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('currency_from', 'currency_to')
    