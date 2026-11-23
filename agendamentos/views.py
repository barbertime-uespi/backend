from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Agendamento


class CancelarAgendamentoView(APIView):
    """RF09 / RN04: Cancela agendamento apenas pelo cliente dono ou Admin."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            agendamento = Agendamento.objects.select_related('cliente').get(pk=pk)
        except Agendamento.DoesNotExist:
            return Response(
                {'detail': 'Agendamento nao encontrado.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        usuario = request.user
        is_admin = bool(getattr(usuario, 'is_staff', False) or getattr(usuario, 'is_superuser', False))
        cliente_usuario = getattr(agendamento.cliente, 'user', None)
        is_dono = cliente_usuario == usuario

        if not (is_admin or is_dono):
            return Response(
                {'detail': 'Voce nao tem permissao para cancelar este agendamento.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        agendamento.status = 'cancelado'
        agendamento.save(update_fields=['status'])

        return Response(
            {'id': agendamento.id, 'status': agendamento.status},
            status=status.HTTP_200_OK,
        )