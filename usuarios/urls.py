from django.urls import path
from .views import (RegistroView, LoginUsuarioView, LogoutUsuarioView, perfil_usuario, 
    EditarCuentaBancariaView, EliminarCuentaBancariaView,
    EditarWalletView, EliminarWalletView)
from . import views
from django.contrib.auth.views import LogoutView

app_name = 'usuarios'

urlpatterns = [
    path('registro/', RegistroView.as_view(), name='registro'),
    path('verificar-email/', views.verificar_email, name='verificar_email'),
    path('recuperar-password/', views.recuperar_password, name='recuperar_password'),
    path('verificar-codigo-recuperacion/', views.verificar_codigo_recuperacion, name='verificar_codigo_recuperacion'),
    path('cambiar-password-recuperacion/', views.cambiar_password_recuperacion, name='cambiar_password_recuperacion'),
    path('login/', LoginUsuarioView.as_view(), name='login'),
    path('logout/', LogoutUsuarioView.as_view(), name='logout'),
    
    path('dashboard/', views.dashboard, name='dashboard'),
    path('nueva_transaccion/', views.nueva_transaccion, name='nueva_transaccion'),
    path('transaccion/confirmar/<int:transaccion_id>/', views.confirmar_transaccion, name='confirmar_transaccion'),
    path('perfil/', perfil_usuario, name='perfil_usuario'),

    path('cuenta/editar/<int:pk>/', EditarCuentaBancariaView.as_view(), name='editar_cuenta_bancaria'),
    path('cuenta/eliminar/<int:pk>/', EliminarCuentaBancariaView.as_view(), name='eliminar_cuenta_bancaria'),

    path('wallet/editar/<int:pk>/', EditarWalletView.as_view(), name='editar_wallet'),
    path('wallet/eliminar/<int:pk>/', EliminarWalletView.as_view(), name='eliminar_wallet'),
]