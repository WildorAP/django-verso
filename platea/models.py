from django.db import models

CURRENCY_CHOICES = [
    ('USD', 'Dólar Estadounidense'),
    ('USDT', 'USDT'),
    ('USDC', 'USDC'),  
    ('PEN', 'Nuevo Sol Peruano'),
]

class ExchangeRate(models.Model):
    currency_from = models.CharField(max_length=4, choices=CURRENCY_CHOICES)
    currency_to = models.CharField(max_length=4, choices=CURRENCY_CHOICES)

    rate_compra = models.DecimalField(max_digits=10, decimal_places=4)
    rate_venta = models.DecimalField(max_digits=10, decimal_places=4)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.currency_from} -> {self.currency_to} | Compra: {self.rate_compra} / Venta: {self.rate_venta}"