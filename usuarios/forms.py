from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
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
            raise forms.ValidationError("Informe um telefone válido com DDD.")
        return telefone


class UsuarioCreationForm(ContatoValidationMixin, UserCreationForm):
    aceite_termos = forms.BooleanField(
        required=True,
        label="Li e concordo com os termos de uso",
        error_messages={
            "required": "Voce precisa concordar com os Termos de Uso para criar a conta.",
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome_completo"].required = True
        self.fields["aceite_termos"].widget.attrs.update({"class": "form-check-input"})

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
        fields = ("email", "nome_completo", "telefone", "foto")
        labels = {
            "nome_completo": "Nome",
        }
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "inputmode": "email"}),
            "nome_completo": forms.TextInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control", "inputmode": "tel", "placeholder": "(00) 00000-0000"}),
            "foto": forms.FileInput(attrs={"class": "d-none", "accept": "image/*"}),
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


class SocialFinalizeSignupForm(ContatoValidationMixin, SocialSignupForm):
    nome_completo = forms.CharField(
        label="Nome completo",
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
    )
    telefone = forms.CharField(
        label="Telefone",
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "inputmode": "tel",
                "placeholder": "(00) 00000-0000",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "email" in self.fields:
            self.fields["email"].widget.attrs.update({"class": "form-control"})

        if self.is_bound:
            return

        sociallogin = getattr(self, "sociallogin", None)
        social_user = getattr(sociallogin, "user", None) if sociallogin else None
        extra = (
            getattr(getattr(sociallogin, "account", None), "extra_data", {}) or {}
            if sociallogin
            else {}
        )

        nome_sugerido = (
            getattr(social_user, "nome_completo", "")
            or extra.get("name")
            or " ".join(
                [
                    p
                    for p in [extra.get("first_name"), extra.get("last_name")]
                    if p
                ]
            ).strip()
        )
        telefone_sugerido = getattr(social_user, "telefone", "")

        if nome_sugerido:
            self.initial.setdefault("nome_completo", nome_sugerido)
        if telefone_sugerido:
            self.initial.setdefault("telefone", telefone_sugerido)

    def save(self, request):
        user = super().save(request)
        user.nome_completo = (self.cleaned_data.get("nome_completo") or "").strip()
        user.telefone = (self.cleaned_data.get("telefone") or "").strip()
        user.save(update_fields=["nome_completo", "telefone"])
        return user
