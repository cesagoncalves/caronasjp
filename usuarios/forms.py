from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm

Usuario = get_user_model()

class UsuarioCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("email", "nome_completo", "telefone", "foto")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "nome_completo": forms.TextInput(attrs={"class": "form-control", "autofocus": True}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "foto": forms.FileInput(attrs={"class": "form-control"}),
        }


class UsuarioProfileForm(UserChangeForm):
    password = None  # Remove campo de senha do formulário de perfil

    class Meta:
        model = Usuario
        fields = ("email", "nome_completo", "telefone")
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "nome_completo": forms.TextInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
        }


class UsuarioPasswordForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
