from django.db import models
from django.conf import settings
import uuid
from django.utils.timezone import now

class Carona(models.Model):
    STATUS_CHOICES = (
        ('ativa', 'Ativa'),
        ('concluida', 'Concluída'),
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


    def __str__(self):
        return f"{self.origem} → {self.destino} às {self.hora}"

    @property
    def vagas_restantes(self):
        # Somente solicitações aceitas
        vagas_ocupadas = self.solicitacoes.filter(status='aceita').aggregate(
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
        return self.data < now().date()

    
class Solicitacao(models.Model):
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('aceita', 'Aceita'),
        ('recusada', 'Recusada'),
    )

    carona = models.ForeignKey(Carona, on_delete=models.CASCADE, related_name="solicitacoes")
    
    solicitante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,  # permite solicitações sem login
        related_name="minhas_solicitacoes"
    )

    nome_solicitante = models.CharField(max_length=100)
    telefone_solicitante = models.CharField(max_length=20)
    visto_passageiro = models.BooleanField(default=True)
    visto_viagem = models.BooleanField(default=False)
    quantidade = models.PositiveIntegerField(default=1)
    data_solicitacao = models.DateTimeField(auto_now_add=True)

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
        return f"{self.nome_solicitante} pediu {self.quantidade} vaga(s)"

class Veiculo(models.Model):

    TIPO_CHOICES = [
        ("carro", "Carro"),
        ("moto", "Moto"),
        ("van", "Van"),
        ("onibus", "Ônibus / Micro-ônibus"),
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
        if self.tipo in ["carro", "moto"]:
            return f"{self.get_tipo_display()} - {self.marca} {self.modelo} ({self.cor})"
        return self.get_tipo_display()

