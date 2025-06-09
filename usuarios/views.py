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
import requests
from .didit_api import DiditAPI
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)


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

    # Obtener información de verificación DIDIT
    perfil = getattr(request.user, 'perfil', None)
    verificacion_completada = perfil.verificacion_didit_completada if perfil else False
    
    # Verificar si necesita información financiera
    info_financiera_faltante = None
    if perfil and verificacion_completada:
        info_financiera_faltante = perfil.obtener_info_financiera_faltante()
    
    return render(request, 'usuarios/dashboard.html', {
        'transacciones': transacciones,
        'tasas': tasas_dict,
        'tasas_json': tasas_json,
        'moneda_origen': moneda_origen,
        'moneda_destino': moneda_destino,
        'monto': monto,
        'monto_convertido': monto_convertido,
        'tasa': tasa,
        'verificacion_completada': verificacion_completada,
        'perfil': perfil,
        'info_financiera_faltante': info_financiera_faltante,
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

        # Enviar notificación por correo al administrador
        try:
            from django.conf import settings
            from .utils import enviar_notificacion_nueva_orden
            
            enviar_notificacion_nueva_orden(transaccion, settings.ADMIN_EMAIL)
            logger.info(f"Notificación de nueva orden enviada para transacción {transaccion.id}")
        except Exception as e:
            logger.error(f"Error al enviar notificación de nueva orden para transacción {transaccion.id}: {str(e)}")
            # No interrumpir el flujo aunque falle el envío del correo

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
    
    # Auto-sincronizar verificación DIDIT si estamos en la sección de seguridad
    # y el usuario tiene sesión activa pero no está completada
    if (seccion == 'seguridad' and 
        perfil.didit_session_id and 
        not perfil.verificacion_didit_completada):
        try:
            import logging
            logger = logging.getLogger('usuarios')
            logger.info(f'Auto-sincronizando estado DIDIT para usuario {user.id} en perfil')
            
            didit_api = DiditAPI()
            status_result = didit_api.get_verification_status(perfil.didit_session_id)
            
            if status_result['success']:
                verification_data = status_result['data']
                status = verification_data.get('status', 'pending')
                
                # Verificar si está aprobado - auto-sincronización
                is_verified = (
                    verification_data.get('is_verified', False) or
                    status == 'completed' or
                    status.lower() == 'approved' or
                    verification_data.get('overall_result', '').lower() == 'approved'
                )
                
                if is_verified:
                    perfil.verificacion_didit_completada = True
                    perfil.fecha_verificacion_didit = timezone.now()
                    perfil.resultado_verificacion_didit = verification_data
                    perfil.save()
                    messages.success(request, '¡Tu verificación de identidad se ha actualizado automáticamente!')
                    logger.info(f'Verificación auto-sincronizada exitosamente para usuario {user.id}')
                        
        except Exception as e:
            import logging
            logger = logging.getLogger('usuarios')
            logger.error(f'Error en auto-sincronización DIDIT para usuario {user.id}: {str(e)}')

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
            # Verificar que el usuario esté verificado con DIDIT
            if not perfil.verificacion_didit_completada:
                messages.error(request, 'Debes verificar tu identidad antes de agregar wallets.')
                return redirect(reverse('usuarios:perfil_usuario') + '?seccion=financiera')
            
            form_wallet = WalletForm(request.POST)
            if form_wallet.is_valid():
                direccion = form_wallet.cleaned_data['direccion']
                red = form_wallet.cleaned_data['red']  # ✅ OBTENER LA RED
                
                # Verificar el estado de la wallet antes de agregarla
                try:
                    resultado_verificacion = verificar_wallet_riesgo(direccion, red)  # ✅ PASAR RED
                    
                    if not resultado_verificacion['valid']:
                        messages.error(request, 'La dirección/correo no es válida. Por favor, verifica los datos.')
                        return redirect(reverse('usuarios:perfil_usuario') + '?seccion=financiera')
                    
                    if resultado_verificacion['riesgo']:
                        messages.error(request, f'Esta wallet presenta factores de riesgo y no puede ser agregada. Factores detectados: {", ".join(resultado_verificacion["detalles_riesgo"]["factores"])}')
                        return redirect(reverse('usuarios:perfil_usuario') + '?seccion=financiera')
                    
                    # Si llegamos aquí, la wallet es válida y operativa
                    wallet = form_wallet.save(commit=False)
                    wallet.usuario = user
                    
                    # ✅ PARA BINANCE PAY SIEMPRE ES OPERATIVO
                    if red == 'BINANCE_PAY':
                        wallet.estado_riesgo = 'OPERATIVO'
                    else:
                        wallet.estado_riesgo = 'OPERATIVO' if not resultado_verificacion['riesgo'] else 'RIESGO'
                    
                    wallet.ultima_verificacion = timezone.now()
                    wallet.save()
                    
                    messages.success(request, f'¡Wallet agregada exitosamente con estado {wallet.get_estado_riesgo_display()}!')
                    return redirect(reverse('usuarios:perfil_usuario') + '?seccion=financiera')
                    
                except Exception as e:
                    messages.error(request, f'Error al verificar la wallet: {str(e)}. Por favor, intenta nuevamente.')
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
    
    def form_valid(self, form):
        # Verificar que el usuario esté verificado con DIDIT
        perfil = getattr(self.request.user, 'perfil', None)
        if not perfil or not perfil.verificacion_didit_completada:
            messages.error(self.request, 'Debes verificar tu identidad antes de editar wallets.')
            return redirect(reverse('usuarios:perfil_usuario') + '?seccion=financiera')
        
        # Obtener la nueva dirección y red
        nueva_direccion = form.cleaned_data['direccion']
        nueva_red = form.cleaned_data['red']  # ✅ OBTENER LA RED
        
        # Si ni la dirección ni la red cambiaron, no necesitamos verificar
        if nueva_direccion == self.object.direccion and nueva_red == self.object.red:
            return super().form_valid(form)
        
        # Verificar el estado de la nueva dirección
        try:
            resultado_verificacion = verificar_wallet_riesgo(nueva_direccion, nueva_red)  # ✅ PASAR RED
            
            if not resultado_verificacion['valid']:
                messages.error(self.request, 'La nueva dirección/correo no es válida. Por favor, verifica los datos.')
                return self.form_invalid(form)
            
            if resultado_verificacion['riesgo']:
                messages.error(self.request, f'La nueva dirección presenta factores de riesgo y no puede ser usada. Factores detectados: {", ".join(resultado_verificacion["detalles_riesgo"]["factores"])}')
                return self.form_invalid(form)
            
            # Si llegamos aquí, la nueva dirección es válida y operativa
            wallet = form.save(commit=False)
            
            # ✅ PARA BINANCE PAY SIEMPRE ES OPERATIVO
            if nueva_red == 'BINANCE_PAY':
                wallet.estado_riesgo = 'OPERATIVO'
            else:
                wallet.estado_riesgo = 'OPERATIVO' if not resultado_verificacion['riesgo'] else 'RIESGO'
            
            wallet.ultima_verificacion = timezone.now()
            wallet.save()
            
            messages.success(self.request, f'¡Wallet actualizada exitosamente con estado {wallet.get_estado_riesgo_display()}!')
            return redirect(self.get_success_url())
            
        except Exception as e:
            messages.error(self.request, f'Error al verificar la nueva dirección: {str(e)}. Por favor, intenta nuevamente.')
            return self.form_invalid(form)

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
            
            # Verificar si necesita verificación DIDIT
            if perfil.verificacion_didit_requerida and not perfil.verificacion_didit_completada:
                return redirect('usuarios:iniciar_verificacion_didit')
            
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

def verificar_wallet_riesgo(direccion, red=None):
    """
    Verifica el riesgo de una wallet
    Para Binance Pay no hace verificación blockchain
    """
    
    # ✅ EXCLUIR BINANCE PAY DE VERIFICACIÓN BLOCKCHAIN
    if red == 'BINANCE_PAY':
        # Para Binance Pay solo validamos que sea un correo válido
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        try:
            validate_email(direccion)
            return {
                'valid': True,
                'riesgo': False,
                'detalles_riesgo': {
                    'factores': [],
                    'total_factores': 0,
                    'fuente': 'Binance Pay - No requiere verificación blockchain'
                }
            }
        except ValidationError:
            return {
                'valid': False,
                'riesgo': False,
                'detalles_riesgo': {
                    'factores': ['Correo electrónico inválido para Binance Pay'],
                    'total_factores': 1,
                    'fuente': 'Validación local'
                }
            }
    
    # ✅ CÓDIGO EXISTENTE PARA OTRAS REDES
    if direccion.startswith('0x'):
        # Ethereum → GoPlusLabs
        url = f"https://api.gopluslabs.io/api/v1/address_security/eth?address={direccion}"
        try:
            r = requests.get(url)
            data = r.json()
            # Debug log removido para producción
            
            # Verificamos si la dirección existe primero usando la respuesta completa
            if data.get("code") == 1:  # La API devuelve código 1 cuando la solicitud es exitosa
                result = data.get("result", {}).get(direccion.lower(), {})
                if not result:
                    # Si no hay datos para esta dirección, intentamos con Etherscan
                    raise Exception("No data found in GoPlusLabs")
                
                # Analizamos diferentes factores de riesgo
                risk_factors = []
                
                # Verificamos si es una dirección maliciosa
                if result.get("is_malicious_address") == "1":
                    risk_factors.append("Dirección marcada como maliciosa")
                
                # Verificamos si es un contrato
                if result.get("is_contract") == "1":
                    risk_factors.append("Es un contrato")
                
                # Verificamos si tiene reportes de phishing
                if result.get("is_phishing_address") == "1":
                    risk_factors.append("Reportada por phishing")
                
                # Verificamos si es una dirección de minería
                if result.get("is_mining_pool_address") == "1":
                    risk_factors.append("Pool de minería")
                
                # Verificamos si es un exchange
                if result.get("is_exchange_address") == "1":
                    risk_factors.append("Dirección de exchange")
                
                # Verificamos si es una dirección de token
                if result.get("is_token_contract") == "1":
                    risk_factors.append("Contrato de token")
                
                # Verificamos si es una dirección de spam
                if result.get("is_spam_address") == "1":
                    risk_factors.append("Marcada como spam")
                
                # Determinamos el nivel de riesgo basado en los factores encontrados
                riesgo = len(risk_factors) > 0
                
                return {
                    'valid': True,
                    'riesgo': riesgo,
                    'detalles_riesgo': {
                        'factores': risk_factors,
                        'total_factores': len(risk_factors),
                        'fuente': 'GoPlusLabs'
                    }
                }
            
            # Si GoPlusLabs no pudo verificar, intentamos con Etherscan
            from django.conf import settings
            etherscan_api_key = getattr(settings, 'ETHERSCAN_API_KEY', None)
            
            if not etherscan_api_key:
                return {
                    'valid': False,
                    'riesgo': False,
                    'detalles_riesgo': {
                        'factores': ["Etherscan API key no configurada"],
                        'total_factores': 1,
                        'fuente': 'Error de configuración'
                    }
                }
            etherscan_url = f"https://api.etherscan.io/api?module=account&action=balance&address={direccion}&tag=latest&apikey={etherscan_api_key}"
            r = requests.get(etherscan_url)
            data = r.json()
            # Debug log removido para producción
            
            # Etherscan devuelve status "1" si la solicitud es exitosa
            if data.get("status") == "1":
                balance = int(data.get("result", "0"))
                
                # Para direcciones Ethereum, necesitamos verificar si realmente existe
                # Usar otra API de Etherscan para verificar si la dirección tiene transacciones
                tx_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={direccion}&startblock=0&endblock=99999999&sort=asc&apikey={etherscan_api_key}"
                tx_response = requests.get(tx_url)
                tx_data = tx_response.json()
                # Debug log removido para producción
                
                # Si la dirección existe, debería tener al menos 1 transacción o un balance > 0
                if tx_data.get("status") == "1":
                    transactions = tx_data.get("result", [])
                    # Debug log removido para producción
                    
                    # Dirección válida si tiene balance > 0 O tiene transacciones
                    if balance > 0 or len(transactions) > 0:
                        return {
                            'valid': True,
                            'riesgo': False,
                            'detalles_riesgo': {
                                'factores': [],
                                'total_factores': 0,
                                'fuente': 'Etherscan',
                                'balance': balance,
                                'transactions': len(transactions)
                            }
                        }
                    else:
                        # Dirección con formato válido pero sin actividad = no existe realmente
                        return {
                            'valid': False,
                            'riesgo': False,
                            'detalles_riesgo': {
                                'factores': ["Dirección sin actividad en la blockchain"],
                                'total_factores': 1,
                                'fuente': 'Etherscan'
                            }
                        }
                else:
                    # Error al verificar transacciones
                    return {
                        'valid': False,
                        'riesgo': False,
                        'detalles_riesgo': {
                            'factores': ["Error al verificar actividad de la dirección"],
                            'total_factores': 1,
                            'fuente': 'Etherscan'
                        }
                    }
            elif data.get("status") == "0":
                error_msg = data.get("result", "Unknown error")
                # Error log removido para producción
                if "Invalid API Key" in error_msg:
                    return {
                        'valid': False,
                        'riesgo': False,
                        'detalles_riesgo': {
                            'factores': ["Error de API key en Etherscan"],
                            'total_factores': 0,
                            'fuente': 'Error'
                        }
                    }
                elif "not a valid Ethereum address" in error_msg.lower():
                    return {
                        'valid': False,
                        'riesgo': False,
                        'detalles_riesgo': {
                            'factores': ["Dirección ETH inválida"],
                            'total_factores': 0,
                            'fuente': 'Error'
                        }
                    }
            
            # No hacer verificación solo por formato - debe ser verificada por API
            # Si llegamos aquí sin datos de la API, la dirección no es válida
            
            return {
                'valid': False,
                'riesgo': False,
                'detalles_riesgo': {
                    'factores': ["No se pudo verificar la dirección"],
                    'total_factores': 0,
                    'fuente': 'Error'
                }
            }
            
        except Exception as e:
            # Error log using Django logging instead of print for production
            import logging
            logger = logging.getLogger('usuarios')
            logger.error(f"Error verificando ETH: {str(e)}")
            # En caso de error, siempre devolver como inválida
            # No podemos garantizar que la dirección sea válida si no la pudimos verificar
            return {
                'valid': False,
                'riesgo': False,
                'detalles_riesgo': {
                    'factores': ["Error al verificar la dirección - No se pudo confirmar validez"],
                    'total_factores': 1,
                    'fuente': 'Error'
                }
            }

    elif direccion.startswith('T'):
        # Tron → Tronscan
        url = f"https://apilist.tronscanapi.com/api/account?address={direccion}"
        try:
            r = requests.get(url)
            data = r.json()
            return {
                'valid': data.get("accountType") is not None,
                'riesgo': False,
                'detalles_riesgo': {
                    'factores': [],
                    'total_factores': 0
                }
            }
        except Exception as e:
            import logging
            logger = logging.getLogger('usuarios')
            logger.error(f"Error verificando TRON: {str(e)}")
            return {
                'valid': False,
                'riesgo': False,
                'detalles_riesgo': {
                    'factores': ["Error al verificar la dirección"],
                    'total_factores': 0
                }
            }

    elif len(direccion) == 44:
        # Solana → RPC
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [direccion, {"encoding": "jsonParsed"}]
        }
        try:
            r = requests.post("https://api.mainnet-beta.solana.com", json=body)
            data = r.json()
            return {
                'valid': data.get("result", {}).get("value") is not None,
                'riesgo': False,
                'detalles_riesgo': {
                    'factores': [],
                    'total_factores': 0
                }
            }
        except Exception as e:
            import logging
            logger = logging.getLogger('usuarios')
            logger.error(f"Error verificando Solana: {str(e)}")
            return {
                'valid': False,
                'riesgo': False,
                'detalles_riesgo': {
                    'factores': ["Error al verificar la dirección"],
                    'total_factores': 0
                }
            }

    return {
        'valid': False,
        'riesgo': False,
        'detalles_riesgo': {
            'factores': ["Formato de dirección no reconocido"],
            'total_factores': 0
        }
    }

@login_required
def verificar_wallet(request, wallet_id):
    wallet = get_object_or_404(Wallet, id=wallet_id, usuario=request.user)
    
    try:
        # Verificar la wallet usando la nueva función
        resultado = verificar_wallet_riesgo(wallet.direccion, wallet.red)  # ✅ PASAR RED
        
        if resultado['valid']:
            if resultado['riesgo']:
                wallet.estado_riesgo = 'RIESGO'
            else:
                wallet.estado_riesgo = 'OPERATIVO'
        else:
            wallet.estado_riesgo = 'NO_EXISTE'
        
        wallet.ultima_verificacion = timezone.now()
        wallet.save()
        
        return JsonResponse({
            'status': 'success',
            'estado': wallet.get_estado_riesgo_display(),
            'clase_estado': {
                'OPERATIVO': 'text-success',
                'RIESGO': 'text-danger',
                'NO_EXISTE': 'text-warning',
                'PENDIENTE': 'text-secondary'
            }.get(wallet.estado_riesgo, ''),
            'detalles_riesgo': resultado['detalles_riesgo']
        })
        
    except Exception as e:
        import logging
        logger = logging.getLogger('usuarios')
        logger.error(f"Error en verificar_wallet: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


# ===============================================
# Verificación DIDIT
# ===============================================

@login_required
def iniciar_verificacion_didit(request):
    """Vista para iniciar el proceso de verificación con DIDIT"""
    perfil = request.user.perfil
    
    # Verificar si ya completó la verificación
    if perfil.verificacion_didit_completada:
        messages.info(request, 'Ya has completado tu verificación de identidad.')
        return redirect('usuarios:perfil_usuario')
    
    if request.method == 'POST':
        try:
            didit_api = DiditAPI()
            
            # Preparar datos del usuario para DIDIT
            user_data = {
                'user_id': request.user.id,
                'email': request.user.email,
                'first_name': perfil.nombre or request.user.first_name,
                'last_name': perfil.apellidos or request.user.last_name,
                'phone': perfil.celular,
                'country': 'PE',  # Perú por defecto
                'webhook_url': request.build_absolute_uri('/usuarios/didit-webhook/'),
                'redirect_url': request.build_absolute_uri('/usuarios/verificacion-completada/'),
                'language': 'es'
            }
            
            # Crear sesión de verificación
            result = didit_api.create_verification_session(user_data)
            
            if result['success']:
                # Guardar información de la sesión
                perfil.didit_session_id = result['session_id']
                perfil.didit_session_url = result['session_url']
                perfil.save()
                
                # Redirigir al usuario a DIDIT para la verificación
                return redirect(result['session_url'])
            else:
                messages.error(request, f'Error al iniciar la verificación: {result["error"]}')
                
        except Exception as e:
            messages.error(request, f'Error inesperado: {str(e)}')
    
    return render(request, 'usuarios/iniciar_verificacion_didit.html', {
        'perfil': perfil
    })

@login_required
def verificacion_completada(request):
    """Vista que muestra el resultado de la verificación DIDIT"""
    import logging
    logger = logging.getLogger('usuarios')
    
    perfil = request.user.perfil
    
    # Si no tiene sesión activa, redirigir
    if not perfil.didit_session_id:
        logger.warning(f'Usuario {request.user.id} llegó a verificacion_completada sin sesión activa')
        messages.error(request, 'No se encontró una sesión de verificación activa.')
        return redirect('usuarios:perfil_usuario')
    
    logger.info(f'Verificando estado de sesión DIDIT {perfil.didit_session_id} para usuario {request.user.id}')
    
    # Verificar si ya está marcado como completado (por webhook)
    if perfil.verificacion_didit_completada:
        logger.info(f'Usuario {request.user.id} ya tiene verificación completada vía webhook')
        context = {
            'perfil': perfil,
            'status': 'completed',
            'verification_data': perfil.resultado_verificacion_didit,
            'verificacion_exitosa': True
        }
        messages.success(request, '¡Tu verificación de identidad ha sido completada exitosamente!')
        return render(request, 'usuarios/verificacion_completada.html', context)
    
    # Obtener el estado actual de la verificación
    try:
        didit_api = DiditAPI()
        status_result = didit_api.get_verification_status(perfil.didit_session_id)
        
        logger.info(f'Respuesta de estado DIDIT: {status_result}')
        
        if status_result['success']:
            verification_data = status_result['data']
            status = verification_data.get('status', 'pending')
            
            logger.info(f'Estado de verificación para usuario {request.user.id}: {status}')
            
            context = {
                'perfil': perfil,
                'status': status,
                'verification_data': verification_data
            }
            
            # Si está completada exitosamente, actualizar el perfil
            # Verificar si está aprobado según el campo is_verified o si el estado es "Approved"
            is_verified = (
                verification_data.get('is_verified', False) or
                status == 'completed' or
                status.lower() == 'approved' or
                verification_data.get('overall_result', '').lower() == 'approved'
            )
            
            if is_verified:
                perfil.verificacion_didit_completada = True
                perfil.fecha_verificacion_didit = timezone.now()
                perfil.resultado_verificacion_didit = verification_data
                perfil.save()
                context['verificacion_exitosa'] = True
                
                # Verificar si necesita información financiera
                info_financiera_faltante = perfil.obtener_info_financiera_faltante()
                context['info_financiera_faltante'] = info_financiera_faltante
                
                messages.success(request, '¡Tu verificación de identidad ha sido completada exitosamente!')
                logger.info(f'Verificación completada exitosamente para usuario {request.user.id}')
            elif status == 'failed' or status.lower() == 'rejected':
                context['verificacion_fallida'] = True
                messages.error(request, 'La verificación de identidad no pudo ser completada. Por favor, inténtalo nuevamente.')
                logger.warning(f'Verificación falló para usuario {request.user.id}')
            elif status == 'pending' or status == 'processing':
                context['verificacion_pendiente'] = True
                messages.info(request, 'Tu verificación está siendo procesada. Te notificaremos cuando esté lista.')
                logger.info(f'Verificación pendiente para usuario {request.user.id}')
            else:
                # Estado desconocido, mostrar como pendiente
                context['verificacion_pendiente'] = True
                messages.info(request, f'Tu verificación está en estado: {status}. Te notificaremos cuando esté lista.')
                logger.info(f'Estado desconocido {status} para usuario {request.user.id}')
                
        else:
            logger.error(f'Error al obtener estado DIDIT para usuario {request.user.id}: {status_result.get("error", "Error desconocido")}')
            # En lugar de mostrar error, mostrar como pendiente
            context = {
                'perfil': perfil, 
                'status': 'pending',
                'verificacion_pendiente': True
            }
            messages.info(request, 'Tu verificación está siendo procesada. Te notificaremos cuando esté lista.')
            
    except Exception as e:
        logger.error(f'Excepción al verificar estado DIDIT para usuario {request.user.id}: {str(e)}')
        # En lugar de mostrar error, mostrar como pendiente
        context = {
            'perfil': perfil, 
            'status': 'pending',
            'verificacion_pendiente': True
        }
        messages.info(request, 'Tu verificación está siendo procesada. Te notificaremos cuando esté lista.')
    
    return render(request, 'usuarios/verificacion_completada.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def didit_webhook(request):
    """Webhook para recibir actualizaciones de DIDIT"""
    try:
        webhook_data = json.loads(request.body)
        didit_api = DiditAPI()
        processed_data = didit_api.process_webhook_data(webhook_data)
        
        session_id = processed_data.get('session_id')
        if not session_id:
            return JsonResponse({'error': 'No session_id provided'}, status=400)
        
        # Buscar el perfil asociado a esta sesión
        try:
            perfil = Perfil.objects.get(didit_session_id=session_id)
        except Perfil.DoesNotExist:
            return JsonResponse({'error': 'Session not found'}, status=404)
        
        # Actualizar el estado del perfil basado en el webhook
        if processed_data.get('is_verified'):
            perfil.verificacion_didit_completada = True
            perfil.fecha_verificacion_didit = timezone.now()
            perfil.resultado_verificacion_didit = processed_data['verification_details']
            perfil.save()
        elif processed_data.get('status') == 'failed':
            # La verificación falló, limpiar la sesión para permitir reintentos
            perfil.didit_session_id = None
            perfil.didit_session_url = None
            perfil.save()
        
        return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def estado_verificacion_didit(request):
    """Vista para mostrar el estado actual de la verificación DIDIT del usuario"""
    perfil = request.user.perfil
    
    context = {
        'perfil': perfil,
        'verificacion_completada': perfil.verificacion_didit_completada,
        'tiene_sesion_activa': bool(perfil.didit_session_id),
        'fecha_verificacion': perfil.fecha_verificacion_didit,
        'resultado_verificacion': perfil.resultado_verificacion_didit
    }
    
    return render(request, 'usuarios/estado_verificacion_didit.html', context)

@login_required  
def test_didit_auth(request):
    """Vista temporal para probar la autenticación de DIDIT"""
    try:
        didit_api = DiditAPI()
        results = didit_api.test_authentication()
        
        context = {
            'results': results,
            'api_key_configured': bool(didit_api.api_key),
            'api_key_preview': f"{didit_api.api_key[:10]}..." if didit_api.api_key else "No configurada",
            'workflow_id_configured': bool(didit_api.workflow_id),
            'workflow_id_preview': f"{didit_api.workflow_id[:10]}..." if didit_api.workflow_id else "No configurado",
            'webhook_secret_configured': bool(didit_api.webhook_secret),
            'base_url': didit_api.base_url
        }
        
        return render(request, 'usuarios/test_didit_auth.html', context)
        
    except Exception as e:
        return render(request, 'usuarios/test_didit_auth.html', {
            'error': str(e),
            'api_key_configured': False,
            'workflow_id_configured': False,
            'webhook_secret_configured': False
        })

@login_required
def sincronizar_verificacion_didit(request):
    """Vista para sincronizar manualmente el estado de verificación DIDIT"""
    import logging
    logger = logging.getLogger('usuarios')
    
    perfil = request.user.perfil
    
    # Verificar que tenga una sesión activa
    if not perfil.didit_session_id:
        messages.error(request, 'No tienes una sesión de verificación activa para sincronizar.')
        return redirect('usuarios:perfil_usuario')
    
    # Si ya está completada, no necesita sincronizar
    if perfil.verificacion_didit_completada:
        messages.info(request, 'Tu verificación ya está completada.')
        return redirect('usuarios:perfil_usuario')
    
    try:
        logger.info(f'Sincronizando estado DIDIT para usuario {request.user.id}, sesión {perfil.didit_session_id}')
        
        didit_api = DiditAPI()
        status_result = didit_api.get_verification_status(perfil.didit_session_id)
        
        if status_result['success']:
            verification_data = status_result['data']
            status = verification_data.get('status', 'pending')
            
            logger.info(f'Estado sincronizado de DIDIT para usuario {request.user.id}: {status}')
            
            # Actualizar según el estado - reconocer "Approved" como exitoso
            # Verificar si está aprobado
            is_verified = (
                verification_data.get('is_verified', False) or
                status == 'completed' or
                status.lower() == 'approved' or
                verification_data.get('overall_result', '').lower() == 'approved'
            )
            
            if is_verified:
                # Verificación exitosa
                perfil.verificacion_didit_completada = True
                perfil.fecha_verificacion_didit = timezone.now()
                perfil.resultado_verificacion_didit = verification_data
                perfil.save()
                
                # Verificar si necesita información financiera
                if perfil.necesita_informacion_financiera():
                    messages.success(request, '¡Excelente! Tu verificación de identidad ha sido completada exitosamente.')
                    messages.info(request, 'Para comenzar a operar, completa tu información financiera en la sección "Información Financiera" de tu perfil.')
                else:
                    messages.success(request, '¡Excelente! Tu verificación de identidad ha sido completada exitosamente.')
                
                logger.info(f'Verificación sincronizada exitosamente para usuario {request.user.id}')
                    
            elif status == 'failed' or status.lower() == 'rejected':
                # Limpiar sesión para permitir reintentos
                perfil.didit_session_id = None
                perfil.didit_session_url = None
                perfil.save()
                
                messages.error(request, 'Tu verificación falló. Puedes intentar nuevamente.')
                logger.warning(f'Verificación falló para usuario {request.user.id}')
                
            elif status in ['pending', 'processing', 'submitted']:
                messages.info(request, 'Tu verificación aún está siendo procesada. Inténtalo más tarde.')
                logger.info(f'Verificación aún pendiente para usuario {request.user.id}: {status}')
                
            elif status == 'expired':
                # Limpiar sesión expirada
                perfil.didit_session_id = None
                perfil.didit_session_url = None
                perfil.save()
                
                messages.warning(request, 'Tu sesión de verificación expiró. Inicia una nueva verificación.')
                logger.warning(f'Sesión DIDIT expirada para usuario {request.user.id}')
                
            else:
                messages.info(request, f'Estado de verificación: {status}. Inténtalo más tarde.')
                logger.info(f'Estado desconocido para usuario {request.user.id}: {status}')
                
        else:
            logger.error(f'Error al sincronizar estado DIDIT para usuario {request.user.id}: {status_result.get("error", "Error desconocido")}')
            messages.error(request, 'No se pudo obtener el estado de tu verificación. Inténtalo más tarde.')
            
    except Exception as e:
        logger.error(f'Excepción al sincronizar estado DIDIT para usuario {request.user.id}: {str(e)}')
        messages.error(request, 'Ocurrió un error al sincronizar tu verificación. Inténtalo más tarde.')
    
    return redirect('usuarios:perfil_usuario')
