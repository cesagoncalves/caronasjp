from django import template
from datetime import datetime, date, timedelta

register = template.Library()

@register.filter
def friendly_datetime(value):
    """
    Formata uma data e hora para exibir 'hoje às X horas', 'amanhã às X horas' ou a data completa.
    Assume que value é um objeto datetime.
    """
    if not isinstance(value, datetime):
        return value  # Retorna como está se não for datetime

    today = date.today()
    tomorrow = today + timedelta(days=1)

    if value.date() == today:
        return f"Hoje às {value.strftime('%H:%M')}"
    elif value.date() == tomorrow:
        return f"Amanhã às {value.strftime('%H:%M')}"
    else:
        return value.strftime('%d/%m/%Y às %H:%M')

@register.filter
def friendly_date(date_obj):
    """
    Formata uma data para exibir 'Hoje', 'Amanhã' ou a data completa.
    """
    if not date_obj:
        return ""
    today = date.today()
    tomorrow = today + timedelta(days=1)

    if date_obj == today:
        return "Hoje"
    elif date_obj == tomorrow:
        return "Amanhã"
    else:
        return date_obj.strftime('%d/%m/%Y')