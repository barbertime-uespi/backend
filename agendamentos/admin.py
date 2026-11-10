from django.contrib import admin

from .models import Agendamento


@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'barbeiro', 'servico', 'data', 'horario_inicio', 'status')
    list_filter = ('status', 'data', 'barbeiro')
    search_fields = ('cliente__nome', 'barbeiro__nome')
    date_hierarchy = 'data'
