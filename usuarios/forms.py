from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Transaccion,Perfil,CuentaBancaria, Wallet
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from .widgets import ArchivoConstanciaWidget


class RegistroUsuarioForm(forms.Form):
    nombre = forms.CharField(max_length=100, label='Nombre')
    apellidos = forms.CharField(max_length=150, label='Apellidos')
    tipo_documento = forms.ChoiceField(
        choices=[
            ('', 'Seleccionar'),
            ('dni', 'DNI'),
            ('ce', 'Carnet de Extranjería'),
            ('pasaporte', 'Pasaporte'),
        ],
        label='Tipo de Documento'
    )
    documento_identidad = forms.CharField(max_length=20, label='Número de Documento')
    celular = forms.CharField(max_length=20, label='Número de Celular')
    email = forms.EmailField(required=True, label='Correo electrónico')
    email_confirm = forms.EmailField(required=True, label='Confirmar correo electrónico')
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        label='Contraseña',
        min_length=8,
        help_text='La contraseña debe tener al menos 8 caracteres.'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password'
        }),
        label='Confirmar contraseña'
    )
    nacionalidad = forms.ChoiceField(
        choices=[
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
        ],
        label='Nacionalidad'
    )
    estado_civil = forms.ChoiceField(
        choices=[
            ('', 'Seleccionar'),
            ('soltero', 'Soltero/a'),
            ('casado', 'Casado/a'),
            ('divorciado', 'Divorciado/a'),
            ('viudo', 'Viudo/a'),
            ('union_libre', 'Unión Libre'),
        ],
        label='Estado Civil'
    )
    ocupacion = forms.CharField(max_length=100, label='Ocupación')
    es_pep = forms.ChoiceField(
        choices=[
            ('', 'Seleccionar'),
            ('si', 'Sí'),
            ('no', 'No'),
        ],
        label='¿Es usted una Persona Expuesta Políticamente (PEP)?'
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:  # Asegurarse de que hay un email para validar
            # Convertir a minúsculas para la comparación
            email = email.lower()
            if User.objects.filter(email__iexact=email).exists():
                raise ValidationError("Este correo ya está registrado.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        email_confirm = cleaned_data.get('email_confirm')
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        # Solo validar si ambos campos de email están presentes
        if email and email_confirm:
            # Convertir ambos a minúsculas para la comparación
            if email.lower() != email_confirm.lower():
                self.add_error('email_confirm', "Las direcciones de correo electrónico no coinciden.")

        if password and password_confirm:
            if password != password_confirm:
                self.add_error('password_confirm', "Las contraseñas no coinciden.")

        return cleaned_data

    def save(self):
        nombre = self.cleaned_data['nombre']
        apellidos = self.cleaned_data['apellidos']
        tipo_documento = self.cleaned_data['tipo_documento']
        documento_identidad = self.cleaned_data['documento_identidad']
        celular = self.cleaned_data['celular']
        email = self.cleaned_data['email'].lower()  # Asegurar que el email se guarde en minúsculas
        password = self.cleaned_data['password']
        nacionalidad = self.cleaned_data['nacionalidad']
        estado_civil = self.cleaned_data['estado_civil']
        ocupacion = self.cleaned_data['ocupacion']
        es_pep = self.cleaned_data['es_pep']

        # Crear usuario
        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=nombre,
                last_name=apellidos
            )
        except Exception as e:
            raise ValidationError(f"Error al crear el usuario: {str(e)}")

        # Actualizar el perfil (que fue creado automáticamente por el signal)
        try:
            perfil = user.perfil  # Obtener el perfil creado por el signal
            perfil.nombre = nombre
            perfil.apellidos = apellidos
            perfil.tipo_documento = tipo_documento
            perfil.documento_identidad = documento_identidad
            perfil.celular = celular
            perfil.nacionalidad = nacionalidad
            perfil.estado_civil = estado_civil
            perfil.ocupacion = ocupacion
            perfil.es_pep = (es_pep == 'si')
            perfil.save()
        except Exception as e:
            # Si hay un error al actualizar el perfil, eliminar el usuario también
            user.delete()
            raise ValidationError(f"Error al guardar el perfil: {str(e)}")

        return user




class LoginConEmailForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico')
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        user = authenticate(username=email, password=password)

        if user is None:
            raise forms.ValidationError("Correo o contraseña incorrectos.")
        
        cleaned_data['user'] = user  
        return cleaned_data

    

class TransaccionForm(forms.Form):
    CRYPTO_CHOICES = [
        ('USDT', 'Tether USD'),
        ('USDC', 'USD Coin'),
    ]
    
    FIAT_CHOICES = [
        ('PEN', 'Soles Peruanos'),
        ('USD', 'Dólares Americanos'),
    ]
    
    TIPO_CHOICES = [
        ('CRYPTO_TO_FIAT', 'Crypto a Fiat'),
        ('FIAT_TO_CRYPTO', 'Fiat a Crypto'),
    ]
    
    tipo_operacion = forms.ChoiceField(choices=TIPO_CHOICES, label='Tipo de operación')
    moneda_origen = forms.ChoiceField(choices=CRYPTO_CHOICES + FIAT_CHOICES, label='Moneda de origen')
    cantidad_origen = forms.DecimalField(max_digits=16, decimal_places=6, label='Cantidad a cambiar')
    moneda_destino = forms.ChoiceField(choices=CRYPTO_CHOICES + FIAT_CHOICES, label='Moneda a recibir')
    
    # Si es crypto a fiat
    direccion_wallet = forms.CharField(max_length=100, required=False, label='Dirección de wallet (solo si envía crypto)')
    
    # Si es fiat a crypto
    cuenta_bancaria = forms.CharField(max_length=100, required=False, label='Número de cuenta (solo si envía fiat)')
    banco = forms.CharField(max_length=100, required=False, label='Banco (solo si envía fiat)')
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_op = cleaned_data.get('tipo_operacion')
        moneda_origen = cleaned_data.get('moneda_origen')
        moneda_destino = cleaned_data.get('moneda_destino')
        
        # Validar que no se elija la misma moneda de origen y destino
        if moneda_origen == moneda_destino:
            raise forms.ValidationError("La moneda de origen y destino no pueden ser iguales")
        
        # Validar que si el tipo es CRYPTO_TO_FIAT, moneda_origen sea crypto y moneda_destino sea fiat
        if tipo_op == 'CRYPTO_TO_FIAT':
            if moneda_origen not in [choice[0] for choice in self.CRYPTO_CHOICES]:
                raise forms.ValidationError("Para Crypto a Fiat, la moneda de origen debe ser cripto")
            if moneda_destino not in [choice[0] for choice in self.FIAT_CHOICES]:
                raise forms.ValidationError("Para Crypto a Fiat, la moneda de destino debe ser fiat")
        
        # Validar para FIAT_TO_CRYPTO
        if tipo_op == 'FIAT_TO_CRYPTO':
            if moneda_origen not in [choice[0] for choice in self.FIAT_CHOICES]:
                raise forms.ValidationError("Para Fiat a Crypto, la moneda de origen debe ser fiat")
            if moneda_destino not in [choice[0] for choice in self.CRYPTO_CHOICES]:
                raise forms.ValidationError("Para Fiat a Crypto, la moneda de destino debe ser cripto")
        
        return cleaned_data

class PerfilForm(forms.ModelForm):
    email = forms.EmailField(
        label='Correo electrónico',
        disabled=True,  # El email no se puede modificar desde aquí
        required=False
    )

    class Meta:
        model = Perfil
        fields = [
            'nombre', 'apellidos', 'tipo_documento', 'documento_identidad',
            'celular', 'nacionalidad', 'estado_civil', 'ocupacion',
            'es_pep'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.initial['email'] = self.instance.user.email

class CuentaBancariaForm(forms.ModelForm):
    class Meta:
        model = CuentaBancaria
        fields = ['banco', 'numero_cuenta', 'cci', 'alias', 'moneda', 'tipo_cuenta']
        widgets = {
            'banco': forms.Select(attrs={'class': 'form-control'}),
            'numero_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'cci': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el código CCI'}),
            'alias': forms.TextInput(attrs={'class': 'form-control'}),
            'moneda': forms.Select(attrs={'class': 'form-control'}),
            'tipo_cuenta': forms.Select(attrs={'class': 'form-control'}),
        }


class WalletForm(forms.ModelForm):
    class Meta:
        model = Wallet
        fields = ['moneda', 'red', 'direccion', 'alias']
        widgets = {
            'moneda': forms.Select(attrs={'class': 'form-control'}),
            'red': forms.Select(attrs={'class': 'form-control', 'id': 'id_red_wallet'}),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control', 
                'id': 'id_direccion_wallet',
                'placeholder': 'Dirección de wallet o correo (para Binance Pay)'
            }),
            'alias': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre para identificar tu wallet (opcional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar ayuda dinámica según la red
        self.fields['direccion'].help_text = "Para redes tradicionales: dirección de wallet. Para Binance Pay: correo electrónico."

class CambiarPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='La contraseña debe tener al menos 8 caracteres.'
    )
    new_password2 = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('Las contraseñas no coinciden.')

        return cleaned_data

    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user

class TransaccionAdminForm(forms.ModelForm):
    class Meta:
        model = Transaccion
        fields = '__all__'
        widgets = {
            'constancia_archivo': ArchivoConstanciaWidget
        }

class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)
    nombre = forms.CharField(max_length=100)
    apellidos = forms.CharField(max_length=100)

    class Meta:
        model = User
        fields = ('email', 'nombre', 'apellidos', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user