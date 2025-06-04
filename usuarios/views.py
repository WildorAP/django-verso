from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView
from django.views import View
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse

from .forms import (
    RegistroUsuarioForm, PerfilForm, TransaccionForm, 
    LoginConEmailForm, CuentaBancariaForm, WalletForm,
    CambiarPasswordForm
)
from .models import Transaccion, Perfil, CuentaBancaria, Wallet, WalletEmpresa, CuentaEmpresa
from platea.models import ExchangeRate
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash
import json
from .utils import enviar_codigo_verificacion, enviar_codigo_verificacion_registro
from django.contrib.auth.models import User
from django.utils import timezone


# ===============================================
# Vistas de Registro, Login y Logout
# ===============================================

class RegistroView(View):
    def get(self, request):
        form = RegistroUsuarioForm()
        return render(request, 'usuarios/registro.html', {'form': form})

    def post(self, request):
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            try:
                # Crear usuario pero no activarlo aún
                user = form.save()
                user.is_active = False
                user.save()

                # Obtener el perfil (creado por el método save de RegistroUsuarioForm)
                perfil = user.perfil

                # Generar y enviar código de verificación
                codigo = perfil.generar_codigo_verificacion_email()
                enviar_codigo_verificacion_registro(
                    user.email,
                    codigo,
                    perfil.nombre
                )

                # Guardar el usuario_id en la sesión para la verificación
                request.session['usuario_verificacion_id'] = user.id

                messages.success(request, 'Te hemos enviado un código de verificación a tu correo electrónico.')
                return redirect('usuarios:verificar_email')
            except Exception as e:
                messages.error(request, f'Error al crear el usuario: {str(e)}')
                return render(request, 'usuarios/registro.html', {'form': form})

        return render(request, 'usuarios/registro.html', {'form': form})

class LoginUsuarioView(View):
    def get(self, request):
        form = LoginConEmailForm()
        return render(request, 'usuarios/login.html', {'form': form})

    def post(self, request):
        form = LoginConEmailForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect(reverse('usuarios:dashboard'))
        return render(request, 'usuarios/login.html', {'form': form})

class LogoutUsuarioView(View):
    def get(self, request):
        from django.contrib.auth import logout
        logout(request)
        return redirect('principal')

    def post(self, request):
        from django.contrib.auth import logout
        logout(request)
        return redirect('principal')


class AgregarCuentaBancariaView(LoginRequiredMixin, CreateView):
    model = CuentaBancaria
    form_class = CuentaBancariaForm
    template_name = 'usuarios/agregar_cuenta_bancaria.html'
    success_url = reverse_lazy('usuarios:perfil_usuario')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class AgregarWalletView(LoginRequiredMixin, CreateView):
    model = Wallet
    form_class = WalletForm
    template_name = 'usuarios/agregar_wallet.html'
    success_url = reverse_lazy('usuarios:perfil_usuario')

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)

# ===============================================
# Dashboard
# ===============================================

@login_required
def dashboard(request):
    # Obtener todas las transacciones del usuario
    transacciones_list = Transaccion.objects.filter(
        usuario=request.user,
        estado__in=['PENDIENTE', 'EN_PROCESO', 'COMPLETADA', 'FACTURADA', "RECHAZADO"]
    ).order_by('-fecha_creacion')

    # Configurar la paginación
    paginator = Paginator(transacciones_list, 5)  # 5 transacciones por página
    page = request.GET.get('page', 1)
    transacciones = paginator.get_page(page)

    tasas_cambio = ExchangeRate.objects.all()
    tasas_dict = {
        f"{t.currency_from}_{t.currency_to}": {
            "compra": float(t.rate_compra),
            "venta": float(t.rate_venta),
        }
        for t in tasas_cambio
    }
    tasas_json = json.dumps(tasas_dict)

    monto = Decimal(request.GET.get('monto', '100'))
    moneda_origen = request.GET.get('moneda_origen', 'USDT')
    moneda_destino = request.GET.get('moneda_destino', 'PEN')
    tipo_operacion = request.GET.get('tipo_operacion', 'venta')  

    key = f"{moneda_origen}_{moneda_destino}"
    tasa = Decimal(tasas_dict.get(key, {}).get(tipo_operacion, 1.0))
    monto_convertido = monto * tasa

    return render(request, 'usuarios/dashboard.html', {
        'transacciones': transacciones,
        'tasas': tasas_dict,
        'tasas_json': tasas_json,
        'moneda_origen': moneda_origen,
        'moneda_destino': moneda_destino,
        'monto': monto,
        'monto_convertido': monto_convertido,
        'tasa': tasa,
    })


# ===============================================
# Nueva Transacción
# ===============================================


@login_required
def nueva_transaccion(request):
    # Obtener parámetros de la URL
    monto = request.GET.get('monto')
    moneda_origen = request.GET.get('moneda_origen')
    moneda_destino = request.GET.get('moneda_destino')
    tipo_operacion = request.GET.get('tipo_operacion')
    tasa_param = request.GET.get('tasa')

    # Si no hay parámetros, redirigir al dashboard
    if not all([monto, moneda_origen, moneda_destino, tipo_operacion, tasa_param]):
        return redirect('usuarios:dashboard')

    # Convertir valores
    try:
        monto = Decimal(monto)
        tasa = Decimal(tasa_param)
    except (TypeError, ValueError, InvalidOperation):
        return redirect('usuarios:dashboard')

    tipo_operacion_interno = 'CRYPTO_TO_FIAT' if tipo_operacion == 'venta' else 'FIAT_TO_CRYPTO'

    # Calcular monto convertido usando la tasa proporcionada
    monto_convertido = monto * tasa if tipo_operacion == 'venta' else monto / tasa

    cuentas = CuentaBancaria.objects.filter(usuario=request.user)
    wallets = Wallet.objects.filter(usuario=request.user)
    cuentas_empresa = CuentaEmpresa.objects.filter(moneda=moneda_origen, activa=True)
    wallets_empresa = WalletEmpresa.objects.filter(
        activa=True,
        moneda=moneda_origen if tipo_operacion_interno == 'CRYPTO_TO_FIAT' else moneda_destino
    )

    errores = []
    cuenta = None
    wallet = None
    cuenta_empresa = None
    wallet_empresa = None

    if request.method == 'POST':
        # Obtenemos siempre ambos, pero usaremos solo el que aplica
        wallet_id_envio = request.POST.get('wallet_id_envio')  # CRYPTO_TO_FIAT
        wallet_id_destino = request.POST.get('wallet_id_destino')  # FIAT_TO_CRYPTO
        cuenta_id = request.POST.get('cuenta_id')  # CRYPTO_TO_FIAT
        cuenta_empresa_id = request.POST.get('cuenta_empresa_id')  # FIAT_TO_CRYPTO
        wallet_empresa_id = request.POST.get('wallet_empresa_id')  # CRYPTO_TO_FIAT
        

        if tipo_operacion_interno == 'FIAT_TO_CRYPTO':
            # ✅ DESTINO = wallet_id_destino
            if not wallet_id_destino:
                errores.append("Debe seleccionar una wallet donde desea recibir el depósito.")
            else:
                wallet = Wallet.objects.filter(id=wallet_id_destino, usuario=request.user).first()
                if not wallet:
                    errores.append("La wallet seleccionada no es válida.")

            if not cuenta_empresa_id:
                errores.append("Debe seleccionar una cuenta de empresa donde realizará el depósito.")
            else:
                cuenta_empresa = CuentaEmpresa.objects.filter(id=cuenta_empresa_id, activa=True).first()
                if not cuenta_empresa:
                    errores.append("La cuenta de empresa seleccionada no es válida.")
            if not cuenta_id:
                 errores.append("Debe seleccionar la cuenta bancaria desde donde realizó el depósito.")
            else:
                cuenta = CuentaBancaria.objects.filter(id=cuenta_id, usuario=request.user).first()
                if not cuenta:
                    errores.append("La cuenta bancaria seleccionada no es válida.")
        
        else:  # CRYPTO_TO_FIAT
            # ✅ ORIGEN = wallet_id_envio
            if not wallet_id_envio:
                errores.append("Debe seleccionar una wallet desde donde está enviando.")
            else:
                wallet = Wallet.objects.filter(id=wallet_id_envio, usuario=request.user).first()
                if not wallet:
                    errores.append("La wallet seleccionada no es válida.")

            if not cuenta_id:
                errores.append("Debe seleccionar su cuenta bancaria para recibir el depósito.")
            else:
                cuenta = CuentaBancaria.objects.filter(id=cuenta_id, usuario=request.user).first()
                if not cuenta:
                    errores.append("La cuenta bancaria seleccionada no es válida.")

            if not wallet_empresa_id:
                errores.append("Debe seleccionar la wallet de la empresa a la que enviará cripto.")
            else:
                wallet_empresa = WalletEmpresa.objects.filter(id=wallet_empresa_id, activa=True).first()
                if not wallet_empresa:
                    errores.append("La wallet de empresa seleccionada no es válida.")

        if not errores:
            transaccion = Transaccion.objects.create(
                usuario=request.user,
                tipo_operacion=tipo_operacion_interno,
                moneda_origen=moneda_origen,
                cantidad_origen=monto,
                moneda_destino=moneda_destino,
                cantidad_destino=monto_convertido,
                tasa_cambio=tasa,
                estado='INICIADA',
                wallet=wallet,
                cuenta_bancaria=cuenta,
                cuenta_empresa=cuenta_empresa,
                wallet_empresa=wallet_empresa,
            )
            return redirect('usuarios:confirmar_transaccion', transaccion_id=transaccion.id)

    context = {
        'monto': monto,
        'moneda_origen': moneda_origen,
        'moneda_destino': moneda_destino,
        'monto_convertido': round(monto_convertido, 2),
        'tasa': tasa,
        'tipo_operacion': tipo_operacion_interno,
        'errores': errores,
        'cuentas': cuentas,
        'wallets': wallets,
        'cuentas_empresa': cuentas_empresa,
        'wallets_empresa': wallets_empresa,
    }

    return render(request, 'usuarios/nueva_transaccion.html', context)

# ===============================================
# Confirmar Transacción
# ===============================================


@login_required
def confirmar_transaccion(request, transaccion_id):
    """Vista para confirmar la transacción y validar constancia de envío o depósito"""
    transaccion = get_object_or_404(Transaccion, id=transaccion_id, usuario=request.user)
    wallet_usuario = transaccion.wallet if transaccion.tipo_operacion == 'FIAT_TO_CRYPTO' else None

    error_constancia = None
    wallet_direccion = None
    wallet_red = None
    cuenta_empresa = None

    # Mostrar la wallet seleccionada si existe
    if transaccion.tipo_operacion == 'CRYPTO_TO_FIAT' and transaccion.wallet_empresa:
        wallet_direccion = transaccion.wallet_empresa.direccion
        wallet_red = transaccion.wallet_empresa.get_red_display()

    # ✅ Obtener cuenta empresa si aplica
    if transaccion.tipo_operacion == 'FIAT_TO_CRYPTO' and transaccion.cuenta_empresa:
        cuenta_empresa = transaccion.cuenta_empresa

    if request.method == 'POST':
        constancia = request.FILES.get('constancia_archivo')

        if not constancia:
            return render(request, 'usuarios/confirmar_transaccion.html', {
                'transaccion': transaccion,
                'wallet_direccion': wallet_direccion,
                'wallet_red': wallet_red,
                'cuenta_empresa': cuenta_empresa,
                'wallet_usuario': wallet_usuario,
                'error_constancia': 'Debes subir tu constancia antes de confirmar.'
            })

        tipos_permitidos = ['application/pdf', 'image/jpeg', 'image/png']
        if constancia.content_type not in tipos_permitidos:
            return render(request, 'usuarios/confirmar_transaccion.html', {
                'transaccion': transaccion,
                'wallet_direccion': wallet_direccion,
                'wallet_red': wallet_red,
                'cuenta_empresa': cuenta_empresa,
                'error_constancia': 'El archivo debe ser PDF, JPG o PNG.'
            })

        transaccion.constancia_archivo = constancia
        transaccion.estado = 'PENDIENTE'
        transaccion.save()

        return redirect(reverse('usuarios:dashboard'))

    return render(request, 'usuarios/confirmar_transaccion.html', {
        'transaccion': transaccion,
        'wallet_direccion': wallet_direccion,
        'wallet_red': wallet_red,
        'cuenta_empresa': cuenta_empresa,
        'wallet_usuario': wallet_usuario,
    })

@login_required
def perfil_usuario(request):
    user = request.user
    perfil, _ = Perfil.objects.get_or_create(user=user)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    password_success = False
    error_message = None
    if request.method == 'GET' and 'password_success' in request.session:
        password_success = request.session.pop('password_success')

    cuentas_bancarias = CuentaBancaria.objects.filter(usuario=user)
    wallets = Wallet.objects.filter(usuario=user)

    seccion = request.GET.get('seccion', 'personal')
    modo = request.GET.get('modo', 'lectura')
    accion = request.GET.get('accion')
    editar_id = request.GET.get('id')

    mostrar_password_form = request.GET.get('mostrar_password_form') == '1'
    codigo_enviado = request.session.get('codigo_enviado', False)
    codigo_verificado = request.session.get('codigo_verificado', False)

    form_personal = PerfilForm(instance=perfil)
    form_cuenta = CuentaBancariaForm()
    form_wallet = WalletForm()
    form_password = CambiarPasswordForm(user=user)

    if request.method == 'POST':
        if 'solicitar_codigo' in request.POST:
            try:
                # Generar y enviar código
                codigo = perfil.generar_codigo_verificacion()
                # Aquí deberías tener una función para enviar el email
                enviar_codigo_verificacion(user.email, codigo)
                
                if is_ajax:
                    return JsonResponse({'success': True})
                else:
                    messages.success(request, 'Código de verificación enviado a tu correo.')
                    request.session['codigo_enviado'] = True
                    return redirect('usuarios:perfil_usuario')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': str(e)})
                else:
                    messages.error(request, f'Error al enviar el código: {str(e)}')
                    return redirect('usuarios:perfil_usuario')

        elif 'codigo_verificacion' in request.POST:
            codigo = request.POST.get('codigo_verificacion')
            if perfil.verificar_codigo(codigo):
                if is_ajax:
                    return JsonResponse({'success': True})
                else:
                    request.session['codigo_verificado'] = True
                    messages.success(request, 'Código verificado correctamente.')
                    return redirect('usuarios:perfil_usuario')
            else:
                if is_ajax:
                    return JsonResponse({'success': False, 'error': 'Código inválido o expirado.'})
                else:
                    messages.error(request, 'Código inválido o expirado.')
                    return redirect('usuarios:perfil_usuario')

        elif 'cambiar_password' in request.POST:
            form_password = CambiarPasswordForm(user=user, data=request.POST)
            if form_password.is_valid():
                form_password.save()
                update_session_auth_hash(request, user)  # Mantener la sesión activa
                if is_ajax:
                    return JsonResponse({'success': True})
                else:
                    messages.success(request, '¡Contraseña actualizada correctamente!')
                    return redirect('usuarios:perfil_usuario')
            else:
                errors = {field: errors[0] for field, errors in form_password.errors.items()}
                if is_ajax:
                    return JsonResponse({'success': False, 'errors': errors})
                else:
                    messages.error(request, 'Por favor, verifica los datos ingresados.')
                    return redirect('usuarios:perfil_usuario')

        elif 'agregar_cuenta' in request.POST:
            form_cuenta = CuentaBancariaForm(request.POST)
            if form_cuenta.is_valid():
                cuenta = form_cuenta.save(commit=False)
                cuenta.usuario = user
                cuenta.save()
                messages.success(request, '¡Cuenta bancaria agregada exitosamente!')
                return redirect(reverse('usuarios:perfil_usuario') + '?seccion=financiera')
            else:
                messages.error(request, 'Por favor, verifica los datos ingresados.')
        
        elif 'agregar_wallet' in request.POST:
            form_wallet = WalletForm(request.POST)
            if form_wallet.is_valid():
                wallet = form_wallet.save(commit=False)
                wallet.usuario = user
                wallet.save()
                messages.success(request, '¡Wallet agregada exitosamente!')
                return redirect(reverse('usuarios:perfil_usuario') + '?seccion=financiera')
            else:
                messages.error(request, 'Por favor, verifica los datos ingresados.')

        elif 'editar_perfil' in request.POST:
            form_personal = PerfilForm(request.POST, instance=perfil)
            if form_personal.is_valid():
                form_personal.save()
                messages.success(request, '¡Perfil actualizado exitosamente!')
                return redirect('usuarios:perfil_usuario')
            else:
                messages.error(request, 'Por favor, verifica los datos ingresados.')

    return render(request, 'usuarios/perfil_usuario.html', {
        'user': user,
        'perfil': perfil,
        'seccion': seccion,
        'modo': modo,
        'form_personal': form_personal,
        'form_cuenta': form_cuenta,
        'form_wallet': form_wallet,
        'form_password': form_password,
        'mostrar_password_form': mostrar_password_form,
        'codigo_enviado': codigo_enviado,
        'codigo_verificado': codigo_verificado,
        'password_success': password_success,
        'error_message': error_message,
        'cuentas_bancarias': cuentas_bancarias,
        'wallets': wallets,
    })


class EditarCuentaBancariaView(LoginRequiredMixin, UpdateView):
    model = CuentaBancaria
    form_class = CuentaBancariaForm
    template_name = 'usuarios/editar_cuenta_bancaria.html'

    def get_success_url(self):
        return reverse_lazy('usuarios:perfil_usuario') + '?seccion=financiera'

class EliminarCuentaBancariaView(LoginRequiredMixin, DeleteView):
    model = CuentaBancaria
    template_name = 'usuarios/eliminar_confirmar.html'

    def get_success_url(self):
        return reverse_lazy('usuarios:perfil_usuario') + '?seccion=financiera'

class EditarWalletView(LoginRequiredMixin, UpdateView):
    model = Wallet
    form_class = WalletForm
    template_name = 'usuarios/editar_wallet.html'

    def get_success_url(self):
        return reverse_lazy('usuarios:perfil_usuario') + '?seccion=financiera'

class EliminarWalletView(LoginRequiredMixin, DeleteView):
    model = Wallet
    template_name = 'usuarios/eliminar_confirmar.html'

    def get_success_url(self):
        return reverse_lazy('usuarios:perfil_usuario') + '?seccion=financiera'

def verificar_email(request):
    usuario_id = request.session.get('usuario_verificacion_id')
    if not usuario_id:
        messages.error(request, 'Sesión de verificación no válida.')
        return redirect('registro')
    
    try:
        user = User.objects.get(id=usuario_id)
        perfil = user.perfil
    except (User.DoesNotExist, Perfil.DoesNotExist):
        messages.error(request, 'Usuario no encontrado.')
        return redirect('registro')
    
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        if perfil.verificar_codigo_email(codigo):
            user.is_active = True
            user.save()
            login(request, user)
            messages.success(request, '¡Tu correo ha sido verificado exitosamente!')
            return redirect('usuarios:perfil_usuario')
        else:
            messages.error(request, 'Código inválido o expirado.')
    
    return render(request, 'usuarios/verificar_email.html')

def recuperar_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            perfil = user.perfil
            
            # Generar y enviar código de verificación
            codigo = perfil.generar_codigo_verificacion()
            enviar_codigo_verificacion(email, codigo)
            
            # Guardar el ID del usuario en la sesión
            request.session['usuario_recuperacion_id'] = user.id
            messages.success(request, 'Te hemos enviado un código de verificación a tu correo electrónico.')
            return redirect('usuarios:verificar_codigo_recuperacion')
        except User.DoesNotExist:
            messages.error(request, 'No existe una cuenta con ese correo electrónico.')
    
    return render(request, 'usuarios/recuperar_password.html')

def verificar_codigo_recuperacion(request):
    usuario_id = request.session.get('usuario_recuperacion_id')
    if not usuario_id:
        messages.error(request, 'Sesión de recuperación no válida.')
        return redirect('usuarios:login')
    
    try:
        user = User.objects.get(id=usuario_id)
        perfil = user.perfil
    except (User.DoesNotExist, Perfil.DoesNotExist):
        messages.error(request, 'Usuario no encontrado.')
        return redirect('usuarios:login')
    
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        if perfil.verificar_codigo(codigo):
            # Si el código es válido, permitir el cambio de contraseña
            return redirect('usuarios:cambiar_password_recuperacion')
        else:
            messages.error(request, 'Código inválido o expirado.')
    
    return render(request, 'usuarios/verificar_codigo_recuperacion.html')

def cambiar_password_recuperacion(request):
    usuario_id = request.session.get('usuario_recuperacion_id')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if not usuario_id:
        messages.error(request, 'Sesión de recuperación no válida.')
        return redirect('usuarios:login')
    
    try:
        user = User.objects.get(id=usuario_id)
    except User.DoesNotExist:
        messages.error(request, 'Usuario no encontrado.')
        return redirect('usuarios:login')
    
    if request.method == 'POST':
        password1 = request.POST.get('new_password1')
        password2 = request.POST.get('new_password2')
        errors = {}
        
        if not password1:
            errors['new_password1'] = 'Este campo es requerido.'
        elif len(password1) < 8:
            errors['new_password1'] = 'La contraseña debe tener al menos 8 caracteres.'
            
        if not password2:
            errors['new_password2'] = 'Este campo es requerido.'
        elif password1 != password2:
            errors['new_password2'] = 'Las contraseñas no coinciden.'
        
        if errors:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': errors})
            else:
                for error in errors.values():
                    messages.error(request, error)
                return render(request, 'usuarios/cambiar_password_recuperacion.html')
        
        try:
            user.set_password(password1)
            user.save()
            # Limpiar la sesión
            del request.session['usuario_recuperacion_id']
            
            if is_ajax:
                return JsonResponse({'success': True})
            else:
                messages.success(request, 'Tu contraseña ha sido actualizada correctamente.')
                return redirect('usuarios:login')
                
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': {'general': str(e)}})
            else:
                messages.error(request, f'Error al actualizar la contraseña: {str(e)}')
    
    return render(request, 'usuarios/cambiar_password_recuperacion.html')
