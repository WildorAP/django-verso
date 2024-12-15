from django.urls import path
from platea import views

urlpatterns = [
    path('',views.render_index, name='principal'),
]