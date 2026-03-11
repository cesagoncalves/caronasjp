from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime
from viagens.models import Carona, Notificacao


class Command(BaseCommand):
    help = 'Conclui automaticamente caronas que passaram 24 horas desde o horÃ¡rio agendado'

    def handle(self, *args, **options):
        # ObtÃ©m o horÃ¡rio atual em BrasÃ­lia
        agora = timezone.localtime(timezone.now())
        
        # Encontra caronas ativas que jÃ¡ completaram 24 horas desde o horÃ¡rio agendado
        caronas_para_concluir = []
        
        for carona in Carona.objects.filter(status='ativa'):
            # Cria um datetime com a data e hora agendada (em BrasÃ­lia)
            horario_agendado_naive = datetime.combine(carona.data, carona.hora)
            horario_agendado = timezone.make_aware(horario_agendado_naive)
            
            # Adiciona 24 horas
            limite_conclusao = horario_agendado + timedelta(hours=24)
            
            # Se passou do limite, marca para conclusÃ£o
            if agora >= limite_conclusao:
                caronas_para_concluir.append(carona)
        
        # Marca as caronas como concluÃ­das
        total = 0
        for carona in caronas_para_concluir:
            carona.status = 'concluida'
            carona.save()

            # Cria notificacao para o motorista
            Notificacao.objects.create(
                usuario=carona.motorista,
                tipo="viagem_concluida",
                titulo="Viagem concluida",
                carona=carona,
                mensagem=f"Sua carona de {carona.origem} para {carona.destino} foi automaticamente concluida."
            )

            solicitacoes_aceitas = (
                carona.solicitacoes
                .select_related("solicitante")
                .filter(status="aceita")
            )

            for s in solicitacoes_aceitas:
                if not s.solicitante:
                    continue

                if s.tipo == "encomenda":
                    titulo = "Encomenda concluida"
                    mensagem = (
                        f"A entrega da sua encomenda para {carona.destino} foi concluida."
                    )
                else:
                    titulo = "Viagem concluida"
                    mensagem = (
                        f"Sua viagem de {carona.origem} para {carona.destino} foi concluida."
                    )

                Notificacao.objects.create(
                    usuario=s.solicitante,
                    tipo="viagem_concluida",
                    titulo=titulo,
                    mensagem=mensagem,
                    carona=carona,
                    solicitacao=s,
                )
            
            total += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'âœ“ {total} carona(s) concluÃ­da(s) automaticamente'
            )
        )

