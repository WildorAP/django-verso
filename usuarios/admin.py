from django.contrib import admin
from django.utils.html import format_html
from .forms import TransaccionAdminForm
from .widgets import ArchivoConstanciaWidget
from .models import Perfil, CuentaBancaria, Wallet, WalletEmpresa,CuentaEmpresa,Transaccion




@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'nombre', 'apellidos', 'documento_identidad', 'celular', 'es_pep')
    search_fields = ('user__email', 'documento_identidad')

@admin.register(CuentaBancaria)
class CuentaBancariaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'banco', 'numero_cuenta', 'alias')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'red', 'direccion', 'alias')

@admin.register(WalletEmpresa)
class WalletEmpresaAdmin(admin.ModelAdmin):
    list_display = ('alias', 'direccion', 'moneda', 'red', 'activa', 'principal')
    list_filter = ('moneda', 'red', 'activa', 'principal')
    list_editable = ('activa', 'principal')

@admin.register(CuentaEmpresa)
class CuentaEmpresaAdmin(admin.ModelAdmin):
    list_display = ('banco', 'numero_cuenta', 'moneda', 'alias', 'activa', 'principal')
    list_filter = ('banco', 'moneda', 'activa', 'principal')

@admin.register(Transaccion)
class TransaccionAdmin(admin.ModelAdmin):
    form = TransaccionAdminForm
    list_display = (
        'id', 'usuario', 'tipo_operacion', 'moneda_origen',
        'cantidad_origen', 'moneda_destino', 'cantidad_destino',
        'estado', 'fecha_creacion',
    )
    list_filter = ('estado', 'tipo_operacion', 'moneda_origen', 'moneda_destino')
    search_fields = ('usuario__username', 'usuario__email')
    list_editable = ('estado',)
    date_hierarchy = 'fecha_creacion'
    autocomplete_fields = ['usuario']


    

    readonly_fields = (
        'usuario', 'tipo_operacion', 'moneda_origen', 'cantidad_origen',
        'moneda_destino', 'cantidad_destino', 'tasa_cambio', 'fecha_creacion'
        ,'cuenta_bancaria','wallet','wallet_empresa','cuenta_empresa'
        , 'info_cuenta_bancaria', 'info_wallet_cliente'
        , 'info_wallet_empresa','info_cuenta_empresa','mostrar_constancia',
    )

    fieldsets = (
        ('📄 Detalles de la Transacción', {
            'fields': (
                'usuario', 'tipo_operacion', 'moneda_origen', 'cantidad_origen',
                'moneda_destino', 'cantidad_destino', 'tasa_cambio', 'fecha_creacion', 'estado'
            )
        }),
        ('🏦 Cuenta del Cliente', {
        'fields': ('info_cuenta_bancaria',)
        }),
        ('🧾 Wallet del Cliente', {
        'fields': ('info_wallet_cliente',)
        }),
        ('🏛️ Cuenta de Empresa', {
        'fields': ('info_cuenta_empresa',)
        }),
         ('💼 Wallet Empresa', {
        'fields': ('info_wallet_empresa',)
        }),
        ('📎 Comprobante', {
        'fields': ('mostrar_constancia',)
        }),
       
    )
    formfield_overrides = {
            Transaccion._meta.get_field("constancia_archivo"): {
                "widget": ArchivoConstanciaWidget
            }
        }
    def info_cuenta_bancaria(self, obj):
        if not obj.cuenta_bancaria:
            return "No registrada"
        return format_html(
            "<b>{}</b><br>Cuenta: <code>{}</code> "
            "<button type='button' onclick=\"navigator.clipboard.writeText('{}')\">📋 Copiar</button>",
            obj.cuenta_bancaria.get_banco_display(),
            obj.cuenta_bancaria.numero_cuenta,
            obj.cuenta_bancaria.numero_cuenta
        )

    def info_wallet_cliente(self, obj):
        if not obj.wallet:
            return "No registrada"
        return format_html(
            "<b>{} ({})</b><br><code>{}</code> <button  type='button' onclick=\"navigator.clipboard.writeText('{}')\">📋</button>",
            obj.wallet.alias or "Sin alias",
            obj.wallet.get_red_display(),
            obj.wallet.direccion,
            obj.wallet.direccion
        )

    def info_wallet_empresa(self, obj):
        if not obj.wallet_empresa:
            return "No asignada"
        return format_html(
            "<b>{} ({})</b><br><code>{}</code> <button type='button' onclick=\"navigator.clipboard.writeText('{}')\">📋</button>",
            obj.wallet_empresa.alias or "Sin alias",
            obj.wallet_empresa.get_red_display(),
            obj.wallet_empresa.direccion,
            obj.wallet_empresa.direccion
        )

    def info_cuenta_empresa(self, obj):
        if not obj.cuenta_empresa:
            return "No asignada"
        return format_html(
            "<b>{}</b><br>Cuenta: <code>{}</code> <button type='button' onclick=\"navigator.clipboard.writeText('{}')\">📋</button><br>"
            "CCI: <code>{}</code> <button onclick=\"navigator.clipboard.writeText('{}')\">📋</button>",
            obj.cuenta_empresa.get_banco_display(),
            obj.cuenta_empresa.numero_cuenta, obj.cuenta_empresa.numero_cuenta,
            obj.cuenta_empresa.cci, obj.cuenta_empresa.cci
        )

    info_wallet_cliente.short_description = "Wallet del Cliente"
    info_wallet_empresa.short_description = "Wallet Empresa"
    info_cuenta_bancaria.short_description = "Cuenta Bancaria del Cliente"
    info_cuenta_empresa.short_description = "Cuenta Bancaria Empresa"

    def mostrar_constancia(self, obj):
        if obj.constancia_archivo:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">📎 Ver constancia </a>',
                obj.constancia_archivo.url
            )
        return format_html('<span class="text-muted">No cargada</span>')

    mostrar_constancia.short_description = "📎 Constancia"

