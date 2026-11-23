from datetime import datetime, time, timedelta
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Agendamento
from .serializers import AgendamentoSerializer


def _eh_admin(user):
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


def _usuario_do_perfil(perfil):
    if perfil is None:
        return None
    return getattr(perfil, "user", None) or getattr(perfil, "usuario", None)


class HorariosDisponiveisView(APIView):
    """RF06: Consulta horarios livres em blocos de 30 minutos."""

    permission_classes = [permissions.AllowAny]

    ABERTURA = time(8, 0)
    FECHAMENTO = time(20, 0)
    INTERVALO_MINUTOS = 30

    def get(self, request):
        barbeiro_id = request.query_params.get("barbeiro_id")
        data_str = request.query_params.get("data")

        if not barbeiro_id or not data_str:
            return Response(
                {"detail": "Informe barbeiro_id e data (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data_consulta = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Formato de data invalido. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agendamentos_ocupados = Agendamento.objects.filter(
            barbeiro_id=barbeiro_id,
            data=data_consulta,
        ).exclude(status=Agendamento.Status.CANCELADO)

        slots_livres = []
        atual = datetime.combine(data_consulta, self.ABERTURA)
        fim_expediente = datetime.combine(data_consulta, self.FECHAMENTO)
        passo = timedelta(minutes=self.INTERVALO_MINUTOS)

        while atual + passo <= fim_expediente:
            inicio_slot = atual.time()
            fim_slot = (atual + passo).time()

            conflita = agendamentos_ocupados.filter(
                horario_inicio__lt=fim_slot,
                horario_fim__gt=inicio_slot,
            ).exists()

            if not conflita:
                slots_livres.append(inicio_slot.strftime("%H:%M"))

            atual += passo

        return Response(
            {
                "barbeiro_id": int(barbeiro_id) if str(barbeiro_id).isdigit() else barbeiro_id,
                "data": data_consulta.isoformat(),
                "horarios_disponiveis": slots_livres,
            },
            status=status.HTTP_200_OK,
        )


class AgendamentoListCreateView(APIView):
    """GET/POST /api/agendamentos/: Lista conforme o papel e cria reserva com validacoes."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        if _eh_admin(user):
            queryset = Agendamento.objects.select_related(
                "cliente", "barbeiro", "servico"
            ).order_by("data", "horario_inicio")
        else:
            queryset = (
                Agendamento.objects.select_related("cliente", "barbeiro", "servico")
                .filter(
                    Q(cliente__user=user)
                    | Q(cliente__usuario=user)
                    | Q(barbeiro__user=user)
                    | Q(barbeiro__usuario=user)
                )
                .distinct()
                .order_by("data", "horario_inicio")
            )

        serializer = AgendamentoSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AgendamentoSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        agendamento = serializer.save()
        output = AgendamentoSerializer(agendamento, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class CancelarAgendamentoView(APIView):
    """RF09 / RN04: Apenas o cliente dono da reserva ou Admin pode cancelar."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            agendamento = Agendamento.objects.select_related("cliente").get(pk=pk)
        except Agendamento.DoesNotExist:
            return Response(
                {"detail": "Agendamento nao encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        dono_user = _usuario_do_perfil(agendamento.cliente)
        if not (_eh_admin(request.user) or dono_user == request.user):
            return Response(
                {"detail": "Voce nao tem permissao para cancelar este agendamento."},
                status=status.HTTP_403_FORBIDDEN,
            )

        agendamento.status = Agendamento.Status.CANCELADO
        agendamento.save(update_fields=["status"])

        return Response(
            {"id": agendamento.id, "status": agendamento.status},
            status=status.HTTP_200_OK,
        )


class ConcluirAgendamentoView(APIView):
    """RF10 / RN05: Apenas barbeiro responsavel ou Admin conclui; bloqueia se cancelado."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            agendamento = Agendamento.objects.select_related("barbeiro").get(pk=pk)
        except Agendamento.DoesNotExist:
            return Response(
                {"detail": "Agendamento nao encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        barbeiro_user = _usuario_do_perfil(agendamento.barbeiro)
        if not (_eh_admin(request.user) or barbeiro_user == request.user):
            return Response(
                {"detail": "Voce nao tem permissao para concluir este agendamento."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if agendamento.status == Agendamento.Status.CANCELADO:
            return Response(
                {"detail": "Nao e possivel concluir um agendamento cancelado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agendamento.status = Agendamento.Status.CONCLUIDO
        agendamento.save(update_fields=["status"])

        return Response(
            {"id": agendamento.id, "status": agendamento.status},
            status=status.HTTP_200_OK,
        )