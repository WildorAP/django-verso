# Generated by Django 5.1.4 on 2025-05-22 01:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0013_transaccion_wallet_empresa'),
    ]

    operations = [
        migrations.CreateModel(
            name='CuentaEmpresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('banco', models.CharField(choices=[('BCP', 'Banco de Crédito del Perú'), ('INTERBANK', 'Interbank'), ('BBVA', 'BBVA')], max_length=50)),
                ('titular', models.CharField(max_length=100)),
                ('numero_cuenta', models.CharField(max_length=50)),
                ('cci', models.CharField(max_length=50)),
                ('moneda', models.CharField(choices=[('PEN', 'Soles'), ('USD', 'Dólares')], max_length=10)),
                ('alias', models.CharField(max_length=100, unique=True)),
                ('activa', models.BooleanField(default=True)),
                ('principal', models.BooleanField(default=False, help_text='Marcar como cuenta principal para recibir pagos.')),
            ],
        ),
    ]
