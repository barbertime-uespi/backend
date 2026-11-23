from django.urls import path
from .views import CancelarAgendamentoView

app_name = 'agendamentos'

urlpatterns = [
    path('<int:pk>/cancelar/', CancelarAgendamentoView.as_view(), name='cancelar-agendamento'),
]