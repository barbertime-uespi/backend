from django.urls import path
from .views import RegistroClienteView

app_name = 'usuarios'

urlpatterns = [
    path('usuarios/cadastro/', RegistroClienteView.as_view(), name='cadastro-cliente'),
]