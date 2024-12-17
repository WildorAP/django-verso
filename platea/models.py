from django.db import models

# Create your models here.
class ExchangeRate(models.Model):
    currency_from = models.CharField(max_length=4, choices=[('USD', 'Dólar Estadounidense'), ('USDT', 'USDT'),('PEN', 'Nuevo Sol Peruano')])
    currency_to = models.CharField(max_length=4, choices=[('USD', 'Dólar Estadounidense'), ('USDT', 'USDT'),('PEN', 'Nuevo Sol Peruano')])
    rate = models.DecimalField(max_digits=10, decimal_places=3)

    def __str__(self):
        return f"{self.currency_from} -> {self.currency_to}: {self.rate}"
