"""Rotas do app servicos. Endpoints (CRUD de serviços) virão nas próximas etapas."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ServicoViewSet

app_name = 'servicos'

router = DefaultRouter()
router.register(r'servicos', ServicoViewSet, basename='servico')

urlpatterns = [
    path('', include(router.urls)),
]
