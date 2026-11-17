from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BarbeiroListView,
    BarbeiroViewSet,
    PerfilUsuarioView,
    RegistroClienteView,
)

app_name = 'usuarios'

router = DefaultRouter()
router.register(r'admin/barbeiros', BarbeiroViewSet, basename='admin-barbeiro')

urlpatterns = [
    path('usuarios/cadastro/', RegistroClienteView.as_view(), name='cadastro-cliente'),
    path('usuarios/perfil/', PerfilUsuarioView.as_view(), name='perfil_usuario'),
    path('barbeiros/', BarbeiroListView.as_view(), name='lista_barbeiros'),
    path('', include(router.urls)),
]
