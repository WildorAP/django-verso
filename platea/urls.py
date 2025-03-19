from django.urls import path
from platea import views
from .views import get_exchange_rate

urlpatterns = [
    path('',views.render_index, name='principal'),
    path('api/rates/', get_exchange_rate, name='get_exchange_rates'),
    path('academy/', views.academy, name='academy'),
    path('empresas/', views.empresas_view, name='empresas'),
]