from django.db import models

# Create your models here.

from django.contrib.auth.models import User

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    
    # Info personal
    nombre = models.CharField(max_length=100, default='')
    apellidos = models.CharField(max_length=100, default='')
    tipo_documento = models.CharField(max_length=50, choices=[
        ('dni', 'DNI'),
        ('ce', 'Carné de extranjería'),
        ('pasaporte', 'Pasaporte')
    ], default='dni')
    documento_identidad = models.CharField(max_length=50, default='')
    celular = models.CharField(max_length=20, default='')
    nacionalidad = models.CharField(max_length=50, choices=[
            ('', 'Seleccionar país'),
            ('argentina', 'Argentina'),
            ('bolivia', 'Bolivia'),
            ('brasil', 'Brasil'),
            ('chile', 'Chile'),
            ('colombia', 'Colombia'),
            ('costa_rica', 'Costa Rica'),
            ('cuba', 'Cuba'),
            ('ecuador', 'Ecuador'),
            ('el_salvador', 'El Salvador'),
            ('guatemala', 'Guatemala'),
            ('haiti', 'Haití'),
            ('honduras', 'Honduras'),
            ('mexico', 'México'),
            ('nicaragua', 'Nicaragua'),
            ('panama', 'Panamá'),
            ('paraguay', 'Paraguay'),
            ('peru', 'Perú'),
            ('republica_dominicana', 'República Dominicana'),
            ('uruguay', 'Uruguay'),
            ('venezuela', 'Venezuela'),
        ],default='Perú')
    estado_civil = models.CharField(max_length=50, choices=[
        ('soltero', 'Soltero'),
        ('casado', 'Casado'),
        ('viudo', 'Viudo'),
        ('divorciado', 'Divorciado'),
        ('union_libre', 'Unión Libre'),
    ], default='soltero')
    ocupacion = models.CharField(max_length=100, default='')
    es_pep = models.BooleanField(default=False)
    email_verificado = models.BooleanField(default=False)
    codigo_verificacion_email = models.CharField(max_length=6, null=True, blank=True)
    codigo_verificacion_email_expira = models.DateTimeField(null=True, blank=True)

    # Campos para verificación de cambio de contraseña
    codigo_verificacion = models.CharField(max_length=6, null=True, blank=True)
    codigo_verificacion_expira = models.DateTimeField(null=True, blank=True)
    cambio_password_verificado = models.BooleanField(default=False)

    def generar_codigo_verificacion_email(self):
        """Genera un nuevo código de verificación para el correo electrónico"""
        import random
        from django.utils import timezone
        from datetime import timedelta
        
        self.codigo_verificacion_email = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.codigo_verificacion_email_expira = timezone.now() + timedelta(hours=24)
        self.email_verificado = False
        self.save()
        return self.codigo_verificacion_email

    def verificar_codigo_email(self, codigo):
        """Verifica el código de verificación de correo electrónico"""
        from django.utils import timezone
        
        if not self.codigo_verificacion_email or not self.codigo_verificacion_email_expira:
            return False
        
        if timezone.now() > self.codigo_verificacion_email_expira:
            return False
        
        if str(self.codigo_verificacion_email) != str(codigo):
            return False
        
        self.email_verificado = True
        self.codigo_verificacion_email = None
        self.codigo_verificacion_email_expira = None
        self.save()
        return True

    def generar_codigo_verificacion(self):
        """Genera un nuevo código de verificación y establece su tiempo de expiración"""
        import random
        from django.utils import timezone
        from datetime import timedelta
        
        # Generar código de 6 dígitos
        self.codigo_verificacion = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        # Establecer tiempo de expiración (15 minutos)
        self.codigo_verificacion_expira = timezone.now() + timedelta(minutes=15)
        self.cambio_password_verificado = False
        self.save()
        return self.codigo_verificacion

    def verificar_codigo(self, codigo):
        """Verifica si el código proporcionado es válido y no ha expirado"""
        from django.utils import timezone
        
        if not self.codigo_verificacion or not self.codigo_verificacion_expira:
            return False
        
        if timezone.now() > self.codigo_verificacion_expira:
            return False
        
        if str(self.codigo_verificacion) != str(codigo):
            return False
        
        self.cambio_password_verificado = True
        self.codigo_verificacion = None
        self.codigo_verificacion_expira = None
        self.save()
        return True



TIPO_OPERACION_CHOICES = [
    ('CRYPTO_TO_FIAT', 'Cripto a Soles/Dólares'),
    ('FIAT_TO_CRYPTO', 'Soles/Dólares a Cripto'),
]

ESTADO_CHOICES = [
    ('PENDIENTE', 'Pendiente'),
    ('COMPLETADA', 'Completada'),
]

class Transaccion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo_operacion = models.CharField(max_length=20, choices=TIPO_OPERACION_CHOICES)
    moneda_origen = models.CharField(max_length=10)
    cantidad_origen = models.DecimalField(max_digits=20, decimal_places=2)
    moneda_destino = models.CharField(max_length=10)
    cantidad_destino = models.DecimalField(max_digits=20, decimal_places=2)
    tasa_cambio = models.DecimalField(max_digits=20, decimal_places=6)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    constancia_archivo = models.FileField(upload_to='constancias/', blank=True, null=True)  # ✅
    wallet = models.ForeignKey('Wallet', null=True, blank=True, on_delete=models.SET_NULL)
    wallet_empresa = models.ForeignKey('WalletEmpresa', null=True, blank=True, on_delete=models.SET_NULL)
    cuenta_empresa = models.ForeignKey('CuentaEmpresa', null=True, blank=True, on_delete=models.SET_NULL, related_name='transacciones')
    cuenta_bancaria = models.ForeignKey('CuentaBancaria', null=True, blank=True, on_delete=models.SET_NULL, related_name='transacciones')
    ESTADO_CHOICES = [
        ('INICIADO', 'Iniciado'),
        ('PENDIENTE', 'Pendiente'),
        ('COMPLETADA', 'Completada'),
        ('FACTURADA', 'Facturada'),
        ('RECHAZADO', 'Rechazado'),
    ]

    estado = models.CharField(max_length=20,choices=ESTADO_CHOICES,default='INICIADO')

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo_operacion} - {self.moneda_origen}->{self.moneda_destino}"
    

class CuentaBancaria(models.Model):
    BANCOS_PERMITIDOS = [
        ('BCP', 'Banco de Crédito del Perú'),
        ('INTERBANK', 'Interbank'),
    ]
    MONEDA_CHOICES = [
        ('PEN', 'PEN'),
        ('USD', 'USD'),
    ]

    TIPO_CUENTA_CHOICES = [
        ('AHO', 'Ahorros'),
        ('COR', 'Corriente'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cuentas_bancarias')
    banco = models.CharField(max_length=50, choices=BANCOS_PERMITIDOS)
    numero_cuenta = models.CharField(max_length=50)
    cci = models.CharField(max_length=20, blank=True, null=True, help_text='Código de Cuenta Interbancario')
    alias = models.CharField(max_length=50, blank=True, null=True)  
    moneda = models.CharField(max_length=3, choices=MONEDA_CHOICES, default='PEN')
    tipo_cuenta = models.CharField(max_length=3, choices=TIPO_CUENTA_CHOICES, default='AHO')

    def __str__(self):
        return f"{self.get_banco_display()} - {self.numero_cuenta}"


class Wallet(models.Model):
    REDES_PERMITIDAS = [
        ('TRC20', 'Trc-20'),
        ('BINANCE', 'Binance PAY'),
    ]

    MONEDA_CHOICES = [
        ('USDT', 'USDT (Tether)'),
        ('USDC', 'USDC (USD Coin)'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallets')
    red = models.CharField(max_length=20, choices=REDES_PERMITIDAS)
    moneda = models.CharField(max_length=10, choices=MONEDA_CHOICES, default='USDT')
    direccion = models.CharField(max_length=100)
    alias = models.CharField(max_length=50, blank=True, null=True)  # opcional

    def __str__(self):
        return f"{self.get_moneda_display()} - {self.get_red_display()} - {self.direccion}"
class WalletEmpresa(models.Model):
    MONEDA_CHOICES = [
        ('USDT', 'USDT'),
        ('USDC', 'USDC'),
    ]

    RED_CHOICES = [
        ('TRC', 'TRC-20'),
        ('ERC', 'ERC-20'),
        ('BEP', 'BEP-20'),
    ]

    moneda = models.CharField(max_length=20, choices=MONEDA_CHOICES)
    red = models.CharField(max_length=20, choices=RED_CHOICES)
    direccion = models.CharField(max_length=100, unique=True)
    alias = models.CharField(max_length=100, unique=True)
    activa = models.BooleanField(default=True)
    principal = models.BooleanField(default=False, help_text="Marca esta wallet como principal para recibir depósitos.")

    def __str__(self):
        return f"{self.alias} ({self.moneda} - {self.get_red_display()})"
    
class CuentaEmpresa(models.Model):
    BANCOS_CHOICES = [
        ('BCP', 'Banco de Crédito del Perú'),
        ('INTERBANK', 'Interbank'),
        ('BBVA', 'BBVA'),
    ]
    MONEDA_CHOICES = [
        ('PEN', 'Soles'),
        ('USD', 'Dólares'),
    ]

    banco = models.CharField(max_length=50, choices=BANCOS_CHOICES)
    titular = models.CharField(max_length=100)
    numero_cuenta = models.CharField(max_length=50)
    cci = models.CharField(max_length=50)
    moneda = models.CharField(max_length=10, choices=MONEDA_CHOICES)
    alias = models.CharField(max_length=100, unique=True)
    activa = models.BooleanField(default=True)
    principal = models.BooleanField(default=False, help_text="Marcar como cuenta principal para recibir pagos.")

    def __str__(self):
        return f"{self.get_banco_display()} - {self.numero_cuenta} ({self.moneda})"