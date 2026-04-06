from django import template
from datetime import datetime, date, timedelta
import re

register = template.Library()


def _telefone_br_digitos(valor):
    if valor is None:
        return ""
    digitos = re.sub(r"\D", "", str(valor))
    if not digitos:
        return ""

    if digitos.startswith("00"):
        digitos = digitos[2:]
    if digitos.startswith("0") and len(digitos) > 11:
        digitos = digitos[1:]

    if digitos.startswith("55"):
        resto = digitos[2:]
        if len(resto) in (10, 11):
            return digitos
        return digitos

    if len(digitos) in (10, 11):
        return f"55{digitos}"

    return digitos

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

@register.filter
def friendly_date_time(date_obj, time_obj):
    """
    Combina date e time em datetime e formata amigavelmente.
    """
    if not date_obj or not time_obj:
        return ""
    dt = datetime.combine(date_obj, time_obj)
    return friendly_datetime(dt)


@register.filter
def whatsapp_br(valor):
    """
    Retorna telefone em apenas digitos para URL do WhatsApp, sempre com 55 quando aplicavel.
    """
    return _telefone_br_digitos(valor)


@register.filter
def tel_br(valor):
    """
    Retorna telefone para href tel:, priorizando formato internacional BR.
    """
    digitos = _telefone_br_digitos(valor)
    if not digitos:
        return ""
    return f"+{digitos}"
