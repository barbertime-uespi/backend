from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Barbeiro, Cliente
from .serializers import (
    BarbeiroSerializer,
    ClienteSerializer,
    RegistroClienteSerializer,
)


class RegistroClienteView(generics.CreateAPIView):
    """RF01 / US01: Cadastro público de clientes."""

    queryset = Cliente.objects.all()
    serializer_class = RegistroClienteSerializer
    permission_classes = [AllowAny]


class PerfilUsuarioView(APIView):
    """Retorna ou atualiza os dados do usuário logado (Cliente ou Barbeiro)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if hasattr(user, 'cliente'):
            data = ClienteSerializer(user.cliente).data
            data['tipo'] = 'cliente'
            return Response(data)

        if hasattr(user, 'barbeiro'):
            data = BarbeiroSerializer(user.barbeiro).data
            data['tipo'] = 'barbeiro'
            return Response(data)

        return Response(
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'tipo': 'admin' if user.is_staff else 'usuario',
            }
        )

    def patch(self, request):
        user = request.user
        if hasattr(user, 'cliente'):
            serializer = ClienteSerializer(user.cliente, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        if hasattr(user, 'barbeiro'):
            serializer = BarbeiroSerializer(user.barbeiro, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(
            {'detail': 'Usuário sem perfil de cliente ou barbeiro vinculado.'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class BarbeiroListView(generics.ListAPIView):
    """Lista barbeiros ativos para seleção no agendamento."""

    queryset = Barbeiro.objects.filter(ativo=True).order_by('nome')
    serializer_class = BarbeiroSerializer
    permission_classes = [AllowAny]


from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class LogoutView(APIView):
    """RF02: logout real invalidando o refresh token (blacklist)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response(
                {'detail': 'O campo "refresh" é obrigatório.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except TokenError:
            return Response(
                {'detail': 'Token inválido ou expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_205_RESET_CONTENT)
