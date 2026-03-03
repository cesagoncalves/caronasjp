from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("viagens", "0017_solicitacao_descricao_item_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="solicitacao",
            name="endereco_solicitante",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
