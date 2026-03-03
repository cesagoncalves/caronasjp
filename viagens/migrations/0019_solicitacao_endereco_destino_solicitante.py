from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("viagens", "0018_solicitacao_endereco_solicitante"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitacao",
            name="endereco_destino_solicitante",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
