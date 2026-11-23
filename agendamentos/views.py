from datetime import datetime, time, timedelta

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.models import Barbeiro, Cliente
from .models import Agendamento
from .serializers import AgendamentoSerializer


def _eh_admin(user):
    return bool(
        getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)
    )


class HorariosDisponiveisView(APIView):
    """RF06: consulta horários livres em blocos de 30 minutos."""

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
            barbeiro_id_int = int(barbeiro_id)
            if barbeiro_id_int <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {"barbeiro_id": "Informe um identificador numérico válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data_consulta = datetime.strptime(data_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return Response(
                {"data": "Formato de data inválido. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not Barbeiro.objects.filter(pk=barbeiro_id_int, ativo=True).exists():
            return Response(
                {"detail": "Barbeiro não encontrado ou inativo."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if data_consulta < timezone.localdate():
            return Response(
                {"data": "Não é possível consultar horários de uma data passada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agendamentos_ocupados = Agendamento.objects.filter(
            barbeiro_id=barbeiro_id_int,
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

            # Para hoje, não oferece horários que já começaram ou passaram.
            if data_consulta == timezone.localdate():
                agora = timezone.localtime().replace(tzinfo=None).time()
                if inicio_slot <= agora:
                    conflita = True

            if not conflita:
                slots_livres.append(inicio_slot.strftime("%H:%M"))
            atual += passo

        return Response(
            {
                "barbeiro_id": barbeiro_id_int,
                "data": data_consulta.isoformat(),
                "horarios_disponiveis": slots_livres,
            },
            status=status.HTTP_200_OK,
        )


class AgendamentoListCreateView(APIView):
    """GET/POST /api/agendamentos/: lista por papel e cria reservas."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        queryset = Agendamento.objects.select_related(
            "cliente", "barbeiro", "servico"
        )

        if _eh_admin(user):
            pass
        else:
            filtros = []
            try:
                cliente = user.cliente
                filtros.append({"cliente": cliente})
            except Cliente.DoesNotExist:
                pass
            try:
                barbeiro = user.barbeiro
                filtros.append({"barbeiro": barbeiro})
            except Barbeiro.DoesNotExist:
                pass

            if not filtros:
                return Response([], status=status.HTTP_200_OK)

            from django.db.models import Q
            condicao = Q()
            for filtro in filtros:
                condicao |= Q(**filtro)
            queryset = queryset.filter(condicao)

        queryset = queryset.order_by("data", "horario_inicio")
        serializer = AgendamentoSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not _eh_admin(request.user):
            try:
                request.user.cliente
            except Cliente.DoesNotExist:
                return Response(
                    {"detail": "Somente clientes ou administradores podem criar agendamentos."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = AgendamentoSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        agendamento = serializer.save()
        output = AgendamentoSerializer(
            agendamento, context={"request": request}
        )
        return Response(output.data, status=status.HTTP_201_CREATED)


class CancelarAgendamentoView(APIView):
    """RF09/RN04: cliente dono ou administrador pode cancelar."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            agendamento = Agendamento.objects.select_related("cliente__user").get(pk=pk)
        except Agendamento.DoesNotExist:
            return Response(
                {"detail": "Agendamento não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not (_eh_admin(request.user) or agendamento.cliente.user_id == request.user.id):
            return Response(
                {"detail": "Você não tem permissão para cancelar este agendamento."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if agendamento.status == Agendamento.Status.CONCLUIDO:
            return Response(
                {"detail": "Não é possível cancelar um agendamento concluído."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if agendamento.status == Agendamento.Status.CANCELADO:
            return Response(
                {"detail": "Este agendamento já está cancelado."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agendamento.status = Agendamento.Status.CANCELADO
        agendamento.save(update_fields=["status"])
        return Response(
            {"id": agendamento.id, "status": agendamento.status},
            status=status.HTTP_200_OK,
        )


class ConcluirAgendamentoView(APIView):
    """RF10/RN05: barbeiro responsável ou administrador conclui."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            agendamento = Agendamento.objects.select_related("barbeiro__user").get(pk=pk)
        except Agendamento.DoesNotExist:
            return Response(
                {"detail": "Agendamento não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        barbeiro_user_id = agendamento.barbeiro.user_id
        if not (_eh_admin(request.user) or barbeiro_user_id == request.user.id):
            return Response(
                {"detail": "Você não tem permissão para concluir este agendamento."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if agendamento.status == Agendamento.Status.CANCELADO:
            return Response(
                {"detail": "Não é possível concluir um agendamento cancelado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if agendamento.status == Agendamento.Status.CONCLUIDO:
            return Response(
                {"detail": "Este agendamento já está concluído."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agendamento.status = Agendamento.Status.CONCLUIDO
        agendamento.save(update_fields=["status"])
        return Response(
            {"id": agendamento.id, "status": agendamento.status},
            status=status.HTTP_200_OK,
        )
