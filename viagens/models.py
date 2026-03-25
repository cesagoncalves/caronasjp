from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
import uuid
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps
from django.utils import timezone

class Carona(models.Model):
    STATUS_CHOICES = (
        ('ativa', 'Ativa'),
        ('concluida', 'ConcluÃ­da'),
        ('cancelada', 'Cancelada'),
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='ativa'
    )

    TIPO_VALOR_CHOICES = (
        ('dinheiro', 'Valor em dinheiro'),
        ('combinar', 'A combinar'),
        ('gratuita', 'Gratuita'),
    )
        
    origem = models.CharField(max_length=100)
    destino = models.CharField(max_length=100)
    data = models.DateField()
    hora = models.TimeField()
    vagas = models.PositiveIntegerField()
    criado_em = models.DateTimeField(auto_now_add=True)
    viagem_atualizada = models.BooleanField(default=False)
    data_edicao = models.DateTimeField(null=True, blank=True)

    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    tipo_valor = models.CharField(
        max_length=10,
        choices=TIPO_VALOR_CHOICES,
        default='combinar'
    )

    valor = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )

    veiculo = models.ForeignKey(
    "Veiculo",
    on_delete=models.SET_NULL,
    null=True,
    blank=True
    )

    observacoes = models.TextField(
        blank=True,
        null=True,
        verbose_name="ObservaÃ§Ãµes"
    )


    def __str__(self):
        return f"{self.origem} â†’ {self.destino} Ã s {self.hora}"

    @property
    def vagas_restantes(self):
        # Somente solicitaÃ§Ãµes aceitas
        vagas_ocupadas = self.solicitacoes.filter(status='aceita', tipo='carona').aggregate(
            total=models.Sum('quantidade')
        )['total'] or 0
        return self.vagas - vagas_ocupadas
    
    @property
    def valor_exibicao(self):
        if self.tipo_valor == 'dinheiro' and self.valor is not None:
            return f"R$ {self.valor:.2f}".replace('.', ',')
        elif self.tipo_valor == 'gratuita':
            return "Gratuita"
        else:
            return "A combinar"
    
    @property
    def esta_concluida(self):
        agora = timezone.localtime(timezone.now())
        data_atual = agora.date()
        hora_atual = agora.time()
        if self.data < data_atual:
            return True
        elif self.data == data_atual:
            return self.hora < hora_atual
        else:
            return False

    
class Solicitacao(models.Model):
    TIPO_CHOICES = (
        ("carona", "Carona"),
        ("encomenda", "Encomenda"),
    )

    OPCOES_MALAS = [
        (0, 'Nenhuma'),
        (1, '1 mala'),
        (2, '2 malas'),
        (3, '3 ou mais malas'),
    ]

    malas = models.IntegerField(
        choices=OPCOES_MALAS,
        default=0
    )

    observacoes = models.TextField(
        blank=True,
        null=True
    )

    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('aceita', 'Aceita'),
        ('recusada', 'Recusada'),
        ('cancelada', 'Cancelada'),
    )

    carona = models.ForeignKey(Carona, on_delete=models.CASCADE, related_name="solicitacoes")
    
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,  # permite solicitaÃ§Ãµes sem login
        related_name="minhas_solicitacoes"
    )

    nome_solicitante = models.CharField(max_length=100)
    telefone_solicitante = models.CharField(max_length=20)
    endereco_solicitante = models.CharField(max_length=255, blank=True, null=True)
    endereco_destino_solicitante = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="carona")
    quantidade = models.PositiveIntegerField(default=1)
    descricao_item = models.TextField(blank=True, null=True)
    foto_encomenda = models.ImageField(upload_to="encomendas/fotos/", blank=True, null=True)
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    viagem_atualizada = models.BooleanField(default=False)
    data_edicao = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pendente'
    )

    uuid_local = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True
    )

    token_cancelamento = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )



    def __str__(self):
        if self.tipo == "encomenda":
            return f"{self.nome_solicitante} pediu envio de encomenda"
        return f"{self.nome_solicitante} pediu {self.quantidade} vaga(s)"

    def clean(self):
        super().clean()
        if self.tipo == "encomenda" and not self.descricao_item:
            raise ValidationError({"descricao_item": "Informe a descriÃ§Ã£o do item."})
    
    def _otimizar_foto_encomenda(self):
        if not self.foto_encomenda:
            return

        imagem = Image.open(self.foto_encomenda)
        imagem = ImageOps.exif_transpose(imagem)

        if imagem.mode not in ("RGB", "L"):
            imagem = imagem.convert("RGB")
        elif imagem.mode == "L":
            imagem = imagem.convert("RGB")

        # Boa qualidade visual com tamanho reduzido para upload e renderizacao.
        imagem.thumbnail((1280, 1280), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        imagem.save(buffer, format="JPEG", quality=78, optimize=True, progressive=True)
        buffer.seek(0)

        nome_base = Path(self.foto_encomenda.name).stem
        self.foto_encomenda.save(
            f"{nome_base}.jpg",
            ContentFile(buffer.read()),
            save=False,
        )

    def save(self, *args, **kwargs):
        if self.foto_encomenda and not self.foto_encomenda._committed:
            self._otimizar_foto_encomenda()
        super().save(*args, **kwargs)

    def mudar_status(self, novo_status):
        if self.status != novo_status:
            self.status = novo_status
            self.save()

            # ðŸ”” Passageiro â€” feedback da aÃ§Ã£o
            if self.solicitante:
                Notificacao.objects.create(
                    usuario=self.solicitante,
                    tipo="viagem_cancelada",
                    titulo=(
                        "Encomenda cancelada"
                        if self.tipo == "encomenda"
                        else "Viagem cancelada"
                    ),
                    mensagem=(
                        "Voce cancelou a encomenda."
                        if self.tipo == "encomenda"
                        else "Voce cancelou a viagem."
                    ),
                    solicitacao=self,
                    carona=self.carona,
                )

            # ðŸ”” Motorista â€” passageiro cancelou
            Notificacao.objects.create(
                usuario=self.carona.motorista,
                tipo="passageiro_cancelou",
                titulo=(
                    "Passageiro cancelou encomenda"
                    if self.tipo == "encomenda"
                    else "Passageiro cancelou"
                ),
                mensagem=(
                    "Um passageiro cancelou a encomenda."
                    if self.tipo == "encomenda"
                    else "Um passageiro cancelou a carona."
                ),
                solicitacao=self,
                carona=self.carona,
            )


class Veiculo(models.Model):

    TIPO_CHOICES = [
        ("carro", "Carro"),
        ("moto", "Moto"),
        ("van", "Van"),
        ("onibus", "Onibus / Micro-onibus"),
    ]

    motorista = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="veiculos"
    )

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)

    marca = models.CharField(max_length=50, blank=True, null=True)
    modelo = models.CharField(max_length=50, blank=True, null=True)
    cor = models.CharField(max_length=30, blank=True, null=True)
    ano = models.PositiveIntegerField(blank=True, null=True)

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        tipo = self.get_tipo_display()
        detalhes = " ".join(
            p for p in [self.marca, self.modelo] if p
        ).strip()

        extras = []
        if self.ano:
            extras.append(str(self.ano))
        if self.cor:
            extras.append(self.cor)

        if detalhes and extras:
            return f"{tipo} - {detalhes} ({' - '.join(extras)})"
        if detalhes:
            return f"{tipo} - {detalhes}"
        if extras:
            return f"{tipo} ({' - '.join(extras)})"
        return tipo

from django.db import models
from django.conf import settings

class Notificacao(models.Model):

    TIPOS = (
        ("solicitacao_recebida", "SolicitaÃ§Ã£o recebida"),
        ("solicitacao_recusada", "SolicitaÃ§Ã£o recusada"),

        ("viagem_aceita", "Viagem confirmada"),
        ("viagem_atualizada", "Viagem atualizada"),
        ("viagem_cancelada", "Viagem cancelada"),
        ("viagem_concluida", "Viagem concluÃ­da"),
        ("passageiro_cancelou", "Passageiro cancelou"),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notificacoes"
    )

    tipo = models.CharField(max_length=40, choices=TIPOS)

    titulo = models.CharField(max_length=120)
    mensagem = models.TextField()

    carona = models.ForeignKey(
        "Carona",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    solicitacao = models.ForeignKey(
        "Solicitacao",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]

    def __str__(self):
        return f"{self.usuario} - {self.titulo}"


