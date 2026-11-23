"""
URL configuration for barbertime project.

Rotas da API são adicionadas por app (usuarios, servicos, agendamentos) nas
próximas etapas. Nesta etapa (estrutura geral) estão disponíveis o admin e as
rotas de autenticação JWT.
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from usuarios.views import LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Autenticação JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/logout/', LogoutView.as_view(), name='token_logout'),

    # Rotas dos apps (serão preenchidas nas próximas etapas)
path('api/', include('usuarios.urls')),
    path('api/', include('servicos.urls')),
    path('api/agendamentos/', include('agendamentos.urls')),
]
