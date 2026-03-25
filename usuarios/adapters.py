import requests
import json
from urllib.parse import unquote
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.files.base import ContentFile
from .migracao_dispositivo import parse_solicitacao_ids, vincular_solicitacoes_dispositivo


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

        raw = request.COOKIES.get("migracao_dispositivo")
        if raw:
            try:
                payload = json.loads(unquote(raw))
            except Exception:
                payload = {}

            migrar = bool(payload.get("migrar"))
            uuid_local = payload.get("uuid_local", "")
            ids = parse_solicitacao_ids(payload.get("solicitacoes_ids", []))
            migradas = vincular_solicitacoes_dispositivo(
                user,
                migrar=migrar,
                uuid_local=uuid_local,
                solicitacao_ids=ids,
            )
            if migradas > 0:
                request.session["clear_local_solicitacoes"] = True

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
