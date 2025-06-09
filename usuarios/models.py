from django.db import models

# Create your models here.

from django.contrib.auth.models import User
from .storage import constancia_upload_path, ConstanciasStorage

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
        ],default='peru')
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

    # Campos para verificación DIDIT
    verificacion_didit_requerida = models.BooleanField(default=True)
    verificacion_didit_completada = models.BooleanField(default=False)
    didit_session_id = models.CharField(max_length=100, null=True, blank=True)
    didit_session_url = models.URLField(max_length=500, null=True, blank=True)
    fecha_verificacion_didit = models.DateTimeField(null=True, blank=True)
    resultado_verificacion_didit = models.JSONField(default=dict, blank=True)

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

    def necesita_informacion_financiera(self):
        """
        Verifica si el usuario necesita completar su información financiera
        """
        # Solo verificar si ya completó la verificación DIDIT
        if not self.verificacion_didit_completada:
            return False
            
        # Verificar si tiene al menos una cuenta bancaria
        tiene_cuenta = self.user.cuentas_bancarias.exists()
        
        # Verificar si tiene al menos una wallet
        tiene_wallet = self.user.wallets.exists()
        
        # Necesita información financiera si no tiene ni cuenta ni wallet
        return not (tiene_cuenta and tiene_wallet)
    
    def obtener_info_financiera_faltante(self):
        """
        Obtiene detalles específicos de qué información financiera falta
        """
        if not self.verificacion_didit_completada:
            return None
            
        faltante = {
            'necesita_cuenta': not self.user.cuentas_bancarias.exists(),
            'necesita_wallet': not self.user.wallets.exists(),
            'total_cuentas': self.user.cuentas_bancarias.count(),
            'total_wallets': self.user.wallets.count()
        }
        
        return faltante

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
    constancia_archivo = models.FileField(
        upload_to=constancia_upload_path, 
        storage=ConstanciasStorage(), 
        blank=True, 
        null=True,
        help_text="Comprobante de la transacción (PDF, JPG, PNG)"
    )  # ✅ Ahora usando AWS S3
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
        ('TRX', 'TRON (TRC-20)'),
        ('ETH', 'Ethereum (ERC-20)'),
        ('SOL', 'Solana'),
        ('BINANCE_PAY', 'Binance Pay'),
    ]

    MONEDA_CHOICES = [
        ('USDT', 'USDT (Tether)'),
        ('USDC', 'USDC (USD Coin)'),
    ]

    ESTADO_RIESGO_CHOICES = [
        ('PENDIENTE', 'Pendiente de Verificación'),
        ('OPERATIVO', 'Operativo'),
        ('RIESGO', 'Riesgo Detectado'),
        ('NO_EXISTE', 'No Existe'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallets')
    red = models.CharField(max_length=20, choices=REDES_PERMITIDAS)
    moneda = models.CharField(max_length=10, choices=MONEDA_CHOICES, default='USDT')
    direccion = models.CharField(max_length=100)
    alias = models.CharField(max_length=50, blank=True, null=True)
    estado_riesgo = models.CharField(
        max_length=20, 
        choices=ESTADO_RIESGO_CHOICES,
        default='PENDIENTE',
        help_text='Estado de riesgo de la wallet'
    )
    ultima_verificacion = models.DateTimeField(null=True, blank=True)

    def clean(self):
        """Validar formato según la red seleccionada"""
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email
        
        if self.red == 'BINANCE_PAY':
            # Para Binance Pay debe ser un correo válido
            try:
                validate_email(self.direccion)
            except ValidationError:
                raise ValidationError({'direccion': 'Para Binance Pay debe ingresar un correo electrónico válido.'})
        else:
            # Para otras redes, validar que NO sea un correo
            if '@' in self.direccion:
                raise ValidationError({'direccion': f'Para {self.get_red_display()} debe ingresar una dirección de wallet, no un correo.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def es_binance_pay(self):
        """Verifica si es una wallet de Binance Pay"""
        return self.red == 'BINANCE_PAY'

    @property
    def identificador_display(self):
        """Devuelve el identificador formateado para mostrar"""
        if self.es_binance_pay:
            return f"📧 {self.direccion}"
        return f"🔗 {self.direccion}"

    def __str__(self):
        if self.es_binance_pay:
            return f"{self.get_moneda_display()} - {self.get_red_display()} - 📧 {self.direccion}"
        return f"{self.get_moneda_display()} - {self.get_red_display()} - {self.direccion}"

    class Meta:
        verbose_name = 'Wallet'
        verbose_name_plural = 'Wallets'

class WalletEmpresa(models.Model):
    MONEDA_CHOICES = [
        ('USDT', 'USDT'),
        ('USDC', 'USDC'),
    ]

    RED_CHOICES = [
        ('TRC', 'TRC-20'),
        ('ERC', 'ERC-20'),
        ('BEP', 'BEP-20'),
        ('BINANCE_PAY', 'Binance Pay')
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