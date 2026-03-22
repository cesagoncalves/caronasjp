from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm

Usuario = get_user_model()

class UsuarioCreationForm(UserCreationForm):
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
        labels = {
            "nome_completo": "Nome",
        }
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "nome_completo": forms.TextInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
        }


class UsuarioPasswordForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))


class UsuarioCompleteProfileForm(forms.ModelForm):
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
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nome_completo"].required = True
        self.fields["telefone"].required = True
