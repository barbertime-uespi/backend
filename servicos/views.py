from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets

from .models import Servico
from .permissions import IsBarbeiroOrAdminOrReadOnly
from .serializers import ServicoSerializer


class ServicoViewSet(viewsets.ModelViewSet):
    """CRUD completo de serviços. Público vê apenas serviços ativos."""

    serializer_class = ServicoSerializer
    permission_classes = [IsBarbeiroOrAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = Servico.objects.prefetch_related('barbeiros').order_by('nome')

        # Barbeiros e admins visualizam também serviços inativos para gerenciamento
        if user.is_authenticated and (user.is_staff or hasattr(user, 'barbeiro')):
            return queryset

        return queryset.filter(ativo=True)