from rest_framework import generics, permissions
from .models import Cliente
from .serializers import RegistroClienteSerializer


class RegistroClienteView(generics.CreateAPIView):
    """RF01 / US01: Cadastro público de clientes."""
    queryset = Cliente.objects.all()
    serializer_class = RegistroClienteSerializer
    permission_classes = [permissions.AllowAny]