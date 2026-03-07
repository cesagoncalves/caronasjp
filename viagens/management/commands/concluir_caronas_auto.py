from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from viagens.models import Carona, Notificacao


class Command(BaseCommand):
    help = 'Conclui automaticamente caronas que passaram 24 horas desde o horário agendado'

    def handle(self, *args, **options):
        # Obtém o horário atual em Brasília
        agora = timezone.localtime(timezone.now())
        
        # Encontra caronas ativas que já completaram 24 horas desde o horário agendado
        caronas_para_concluir = []
        
        for carona in Carona.objects.filter(status='ativa'):
            # Cria um datetime com a data e hora agendada (em Brasília)
            horario_agendado_naive = datetime.combine(carona.data, carona.hora)
            horario_agendado = timezone.make_aware(horario_agendado_naive)
            
            # Adiciona 24 horas
            limite_conclusao = horario_agendado + timedelta(hours=24)
            
            # Se passou do limite, marca para conclusão
            if agora >= limite_conclusao:
                caronas_para_concluir.append(carona)
        
        # Marca as caronas como concluídas
        total = 0
        for carona in caronas_para_concluir:
            carona.status = 'concluida'
            carona.save()
            
            # Cria notificação para o motorista
            Notificacao.objects.create(
                usuario=carona.motorista,
                tipo='viagem_concluida',
                carona=carona,
                mensagem=f"Sua carona de {carona.origem} para {carona.destino} foi automaticamente concluída."
            )
            
            total += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✓ {total} carona(s) concluída(s) automaticamente'
            )
        )
