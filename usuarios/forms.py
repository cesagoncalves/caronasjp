from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
import re

Usuario = get_user_model()


class ContatoValidationMixin:
    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email
        if "@" not in email or "." not in email.split("@")[-1]:
            raise forms.ValidationError("Informe um email valido.")
        return email

    def clean_telefone(self):
        telefone = (self.cleaned_data.get("telefone") or "").strip()
        if not telefone:
            return telefone
        digitos = re.sub(r"\D", "", telefone)
        if len(digitos) not in (10, 11):
            raise forms.ValidationError("Informe um telefone valido com DDD.")
        return telefone


class UsuarioCreationForm(ContatoValidationMixin, UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome_completo"].required = True

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email", "nome_completo", "telefone", "foto")
        labels = {
            "nome_completo": "Nome",
        }
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "inputmode": "email"}),
            "nome_completo": forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
            "telefone": forms.TextInput(attrs={"class": "form-control", "inputmode": "tel", "placeholder": "(00) 00000-0000"}),
            "foto": forms.FileInput(attrs={"class": "form-control"}),
        }


class UsuarioProfileForm(ContatoValidationMixin, UserChangeForm):
    password = None  # Remove campo de senha do formulário de perfil

    class Meta:
        model = Usuario
        fields = ("email", "nome_completo", "telefone")
        labels = {
            "nome_completo": "Nome",
        }
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "inputmode": "email"}),
            "nome_completo": forms.TextInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control", "inputmode": "tel", "placeholder": "(00) 00000-0000"}),
        }


class UsuarioPasswordForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))


class UsuarioCompleteProfileForm(ContatoValidationMixin, forms.ModelForm):
    email = forms.EmailField(
        required=False,
        disabled=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Usuario
        fields = ("email", "nome_completo", "telefone")
        labels = {
            "nome_completo": "Nome completo",
            "telefone": "Telefone",
        }
        widgets = {
            "nome_completo": forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
            "telefone": forms.TextInput(attrs={"class": "form-control", "inputmode": "tel", "placeholder": "(00) 00000-0000"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome_completo"].required = True
        self.fields["telefone"].required = True
