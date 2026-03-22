from django.db.models.signals import post_save
from django.dispatch import receiver

from viagens.models import Notificacao
from usuarios.push import send_push_to_user


@receiver(post_save, sender=Notificacao)
def push_on_notificacao(sender, instance, created, **kwargs):
    if not created:
        return

    send_push_to_user(
        instance.usuario,
        title=instance.titulo,
        body=instance.mensagem,
        url="/",
    )
