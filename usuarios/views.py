from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Barbeiro, Cliente
from .serializers import (
    BarbeiroSerializer,
    ClienteSerializer,
    RegistroBarbeiroSerializer,
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


class BarbeiroViewSet(viewsets.ModelViewSet):
    """US03/RF03: CRUD de barbeiros restrito ao administrador."""

    queryset = Barbeiro.objects.all().order_by('nome')
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return RegistroBarbeiroSerializer
        return BarbeiroSerializer

    def perform_destroy(self, instance):
        # Soft delete: preserva histórico e FKs de agendamentos.
        instance.ativo = False
        instance.save(update_fields=['ativo'])
