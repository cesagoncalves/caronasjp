from django import forms
import re

from .models import Carona, Solicitacao, Veiculo


def _normalizar_telefone_br(telefone):
    base = (telefone or "").strip()
    if not base:
        raise forms.ValidationError("Informe um telefone para contato.")

    digitos = re.sub(r"\D", "", base)
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]

    if len(digitos) not in (10, 11):
        raise forms.ValidationError("Informe um telefone valido com DDD.")

    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"


class CaronaForm(forms.ModelForm):
    class Meta:
        model = Carona
        fields = [
            "origem",
            "destino",
            "data",
            "hora",
            "vagas",
            "modalidade",
            "tipo_valor",
            "valor",
            "veiculo",
            "observacoes",
        ]
        widgets = {
            "data": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"},
            ),
            "hora": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "vagas": forms.NumberInput(attrs={"min": 1, "class": "form-control"}),
            "valor": forms.NumberInput(
                attrs={"step": "0.01", "placeholder": "Ex: 15,00", "class": "form-control"}
            ),
            "observacoes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Ex: Não levo animais, saída pontual, posso parar no caminho...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["data"].input_formats = ["%Y-%m-%d"]

        if user:
            self.fields["veiculo"].queryset = Veiculo.objects.filter(motorista=user)

        self.fields["veiculo"].empty_label = "Selecione um veiculo"

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
        self.fields["vagas"].required = False
        self.fields["tipo_valor"].required = False
        self.fields["vagas"].widget.attrs["min"] = 0

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo_valor")
        valor = cleaned_data.get("valor")
        veiculo = cleaned_data.get("veiculo")
        modalidade = cleaned_data.get("modalidade")
        vagas = cleaned_data.get("vagas")
        if modalidade == "encomenda":
            cleaned_data["vagas"] = 0
            cleaned_data["tipo_valor"] = tipo = "combinar"
        elif not vagas or vagas < 1:
            self.add_error("vagas", "Informe pelo menos uma vaga para passageiros.")
        if modalidade != "encomenda" and not tipo:
            self.add_error("tipo_valor", "Selecione como será cobrada a passagem.")

        if self.instance.pk:
            ativas = self.instance.solicitacoes.filter(status__in=["pendente", "aceita"])
            if modalidade == "encomenda" and ativas.filter(tipo="carona").exists():
                self.add_error("modalidade", "Há passageiros pendentes ou confirmados nesta viagem.")
            if modalidade == "carona" and ativas.filter(tipo="encomenda").exists():
                self.add_error("modalidade", "Há encomendas pendentes ou confirmadas nesta viagem.")
            from django.db.models import Sum
            ocupadas = ativas.filter(tipo="carona", status="aceita").aggregate(total=Sum("quantidade"))["total"] or 0
            if (cleaned_data.get("vagas") or 0) < ocupadas:
                self.add_error("vagas", f"Já existem {ocupadas} vagas confirmadas.")

        if tipo == "dinheiro" and not valor:
            self.add_error("valor", "Informe o valor da passagem.")

        if tipo != "dinheiro":
            cleaned_data["valor"] = None

        if not veiculo:
            self.add_error("veiculo", "Selecione um veiculo para oferecer carona.")

        return cleaned_data


class SolicitacaoForm(forms.ModelForm):
    quantidade = forms.IntegerField(min_value=1)
    ciente_observacoes = forms.BooleanField(
        required=False,
        label="Li e estou ciente das observações do motorista.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, vagas_disponiveis=None, exigir_ciencia_observacoes=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.vagas_disponiveis = vagas_disponiveis
        if exigir_ciencia_observacoes:
            self.fields["ciente_observacoes"].required = True
        else:
            self.fields.pop("ciente_observacoes", None)
        self.fields["quantidade"].widget.attrs.update({"class": "form-control", "min": 1})
        if vagas_disponiveis is not None:
            self.fields["quantidade"].widget.attrs["max"] = vagas_disponiveis

    def clean_quantidade(self):
        quantidade = self.cleaned_data["quantidade"]
        if self.vagas_disponiveis is not None and quantidade > self.vagas_disponiveis:
            raise forms.ValidationError(f"Só restam {self.vagas_disponiveis} vagas disponíveis.")
        return quantidade

    class Meta:
        model = Solicitacao
        fields = [
            "nome_solicitante",
            "telefone_solicitante",
            "endereco_solicitante",
            "endereco_destino_solicitante",
            "quantidade",
            "malas",
            "observacoes",
        ]
        widgets = {
            "nome_solicitante": forms.TextInput(attrs={"class": "form-control"}),
            "telefone_solicitante": forms.TextInput(attrs={"class": "form-control"}),
            "endereco_solicitante": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Rua, numero, bairro"}
            ),
            "endereco_destino_solicitante": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Rua, numero, bairro"}
            ),
            "quantidade": forms.NumberInput(attrs={"class": "form-control"}),
            "malas": forms.Select(attrs={"class": "form-select"}),
            "observacoes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Ex: Mochila, mala grande, etc."}
            ),
        }

    def clean_endereco_solicitante(self):
        endereco = (self.cleaned_data.get("endereco_solicitante") or "").strip()
        if not endereco:
            raise forms.ValidationError("Informe o endereco para embarque.")
        return endereco

    def clean_endereco_destino_solicitante(self):
        endereco = (self.cleaned_data.get("endereco_destino_solicitante") or "").strip()
        if not endereco:
            raise forms.ValidationError("Informe o endereco de destino.")
        return endereco

    def clean_telefone_solicitante(self):
        return _normalizar_telefone_br(self.cleaned_data.get("telefone_solicitante"))


class EncomendaForm(forms.ModelForm):
    ciente_observacoes = forms.BooleanField(
        required=False,
        label="Li e estou ciente das observações do motorista.",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, exigir_ciencia_observacoes=False, **kwargs):
        super().__init__(*args, **kwargs)
        if exigir_ciencia_observacoes:
            self.fields["ciente_observacoes"].required = True
        else:
            self.fields.pop("ciente_observacoes", None)

    class Meta:
        model = Solicitacao
        fields = [
            "nome_solicitante",
            "telefone_solicitante",
            "endereco_solicitante",
            "endereco_destino_solicitante",
            "descricao_item",
            "foto_encomenda",
            "observacoes",
        ]
        widgets = {
            "nome_solicitante": forms.TextInput(attrs={"class": "form-control"}),
            "telefone_solicitante": forms.TextInput(attrs={"class": "form-control"}),
            "endereco_solicitante": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Rua, numero, bairro"}
            ),
            "endereco_destino_solicitante": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Rua, numero, bairro"}
            ),
            "descricao_item": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Descreva o item da encomenda"}
            ),
            "foto_encomenda": forms.FileInput(attrs={"class": "form-control"}),
            "observacoes": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Ex: Frágil, manter em pé, entregar até 18h..."}
            ),
        }

    def clean_descricao_item(self):
        descricao = (self.cleaned_data.get("descricao_item") or "").strip()
        if not descricao:
            raise forms.ValidationError("Informe a descricao do item.")
        return descricao

    def clean_endereco_solicitante(self):
        endereco = (self.cleaned_data.get("endereco_solicitante") or "").strip()
        if not endereco:
            raise forms.ValidationError("Informe o endereco de coleta/entrega.")
        return endereco

    def clean_endereco_destino_solicitante(self):
        endereco = (self.cleaned_data.get("endereco_destino_solicitante") or "").strip()
        if not endereco:
            raise forms.ValidationError("Informe o endereco de entrega.")
        return endereco

    def clean_telefone_solicitante(self):
        return _normalizar_telefone_br(self.cleaned_data.get("telefone_solicitante"))


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = ["tipo", "marca", "modelo", "cor", "ano"]
        widgets = {
            "marca": forms.TextInput(attrs={"class": "form-control"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
            "cor": forms.TextInput(attrs={"class": "form-control"}),
            "ano": forms.NumberInput(attrs={"class": "form-control", "min": 1900, "max": 2100}),
        }

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get("tipo")

        if tipo in ["carro", "moto"]:
            for campo in ["marca", "modelo", "cor", "ano"]:
                if not cleaned.get(campo):
                    self.add_error(campo, "Campo obrigatorio para carro ou moto")
        return cleaned
