from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("viagens", "0020_alter_carona_observacoes_alter_carona_status_and_more")]

    operations = [
        migrations.AddField(
            model_name="carona", name="modalidade",
            field=models.CharField(max_length=10, default="ambos", choices=[("ambos", "Passageiros e encomendas"), ("carona", "Somente passageiros"), ("encomenda", "Somente encomendas")]),
        ),
        migrations.AlterField(
            model_name="carona", name="tipo_valor",
            field=models.CharField(max_length=10, default="dinheiro", choices=[("dinheiro", "Valor em dinheiro"), ("combinar", "A combinar"), ("gratuita", "Gratuita")]),
        ),
    ]
