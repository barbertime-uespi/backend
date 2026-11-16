from django.urls import path
from .views import RegistroClienteView
from .views import BarbeiroListView, PerfilUsuarioView, RegistroClienteView

app_name = 'usuarios'

urlpatterns = [
    path('usuarios/cadastro/', RegistroClienteView.as_view(), name='cadastro-cliente'),
    path('usuarios/perfil/', PerfilUsuarioView.as_view(), name='perfil_usuario'),
    path('barbeiros/', BarbeiroListView.as_view(), name='lista_barbeiros'),
]
from django.urls import path

