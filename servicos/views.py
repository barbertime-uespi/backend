from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import Servico
from .permissions import IsAdminOrReadOnly
from .serializers import ServicoSerializer


class ServicoViewSet(viewsets.ModelViewSet):
    """CRUD de serviços; consultas públicas mostram somente serviços ativos."""

    serializer_class = ServicoSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Servico.objects.prefetch_related('barbeiros').order_by('nome')
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return queryset
        return queryset.filter(ativo=True)

    def perform_destroy(self, instance):
        """DELETE realiza desativação lógica e preserva o histórico de reservas."""
        instance.ativo = False
        instance.save(update_fields=['ativo'])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
