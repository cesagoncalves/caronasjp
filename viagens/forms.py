from django import forms
from .models import Carona, Solicitacao, Veiculo


class CaronaForm(forms.ModelForm):
    class Meta:
        model = Carona
        fields = [
            'origem',
            'destino',
            'data',
            'hora',
            'vagas',
            'tipo_valor',
            'valor',
            'veiculo',
        ]
        widgets = {
            'data': forms.DateInput(
                format='%Y-%m-%d',  # 🔥 CORREÇÃO
                attrs={
                    'type': 'date',
                    'class': 'form-control',
                }
            ),
            'hora': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control',
            }),
            'vagas': forms.NumberInput(attrs={
                'min': 1,
                'class': 'form-control',
            }),
            'valor': forms.NumberInput(attrs={
                'step': '0.01',
                'placeholder': 'Ex: 15,00',
                'class': 'form-control',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['data'].input_formats = ['%Y-%m-%d']

        # Filtra veículos do motorista logado
        if user:
            self.fields['veiculo'].queryset = Veiculo.objects.filter(
                motorista=user
            )

        self.fields['veiculo'].empty_label = 'Selecione um veículo'

        # Garante Bootstrap em todos os campos
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_valor')
        valor = cleaned_data.get('valor')

        if tipo == 'dinheiro' and not valor:
            self.add_error(
                'valor',
                'Informe o valor da passagem.'
            )

        if tipo != 'dinheiro':
            cleaned_data['valor'] = None

        return cleaned_data


class SolicitacaoForm(forms.ModelForm):
    quantidade = forms.IntegerField(min_value=1)

    class Meta:
        model = Solicitacao
        fields = ["nome_solicitante", "telefone_solicitante", "quantidade"]
        widgets = {
            "nome_solicitante": forms.TextInput(attrs={"class": "form-control"}),
            "telefone_solicitante": forms.TextInput(attrs={"class": "form-control"}),
            "quantidade": forms.NumberInput(attrs={"class": "form-control"}),
        }

class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = ["tipo", "marca", "modelo", "cor", "ano"]
        widgets = {
            "marca": forms.TextInput(attrs={"class": "form-control"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
            "cor": forms.TextInput(attrs={"class": "form-control"}),
            "ano": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1900,
                "max": 2100,
            }),
        }

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")

        if tipo in ["carro", "moto"]:
            for campo in ["marca", "modelo", "cor", "ano"]:
                if not cleaned.get(campo):
                    self.add_error(
                        campo,
                        "Campo obrigatório para carro ou moto"
                    )
        return cleaned


