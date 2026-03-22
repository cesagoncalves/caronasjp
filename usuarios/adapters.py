import requests
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.files.base import ContentFile


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        full_name = (
            data.get("name")
            or data.get("full_name")
            or data.get("display_name")
            or data.get("first_name")
        )
        if not full_name:
            first = data.get("first_name")
            last = data.get("last_name")
            if first or last:
                full_name = " ".join([part for part in [first, last] if part])
        if full_name and not user.nome_completo:
            user.nome_completo = full_name

        phone = data.get("phone") or data.get("phone_number")
        if phone and not user.telefone:
            user.telefone = phone

        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)

        if not user.foto:
            avatar_url = sociallogin.account.get_avatar_url()
            if avatar_url:
                try:
                    response = requests.get(avatar_url, timeout=8)
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "")
                    ext = ".jpg"
                    if "png" in content_type:
                        ext = ".png"
                    filename = f"social_{user.pk}{ext}"
                    user.foto.save(filename, ContentFile(response.content), save=True)
                except Exception:
                    pass

        return user
