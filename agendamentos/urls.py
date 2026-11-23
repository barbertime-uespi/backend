from django.urls import path
from .views import (
    AgendamentoListCreateView,
    CancelarAgendamentoView,
    ConcluirAgendamentoView,
    HorariosDisponiveisView,
)

app_name = "agendamentos"

urlpatterns = [
    path("", AgendamentoListCreateView.as_view(), name="agendamento-list"),
    path("disponiveis/", HorariosDisponiveisView.as_view(), name="disponiveis"),
    path("<int:pk>/cancelar/", CancelarAgendamentoView.as_view(), name="cancelar-agendamento"),
    path("<int:pk>/concluir/", ConcluirAgendamentoView.as_view(), name="concluir-agendamento"),
]