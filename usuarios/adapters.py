import requests
import json
from urllib.parse import unquote
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.files.base import ContentFile
from .migracao_dispositivo import parse_solicitacao_ids, vincular_solicitacoes_dispositivo


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def _resolver_avatar_facebook(self, account, extra):
        picture = extra.get("picture")
        if isinstance(picture, dict):
            data = picture.get("data") or {}
            url = data.get("url")
            if url:
                return url
        if isinstance(picture, str) and picture:
            return picture
        if account.uid:
            # Fallback simples para garantir foto mesmo em menor resolucao.
            return f"https://graph.facebook.com/{account.uid}/picture?type=normal"
        return None

    def _resolver_avatar_url(self, sociallogin):
        account = sociallogin.account
        extra = account.extra_data or {}
        provider = (account.provider or "").lower()

        if provider == "facebook":
            return self._resolver_avatar_facebook(account, extra)

        if provider == "google":
            picture = extra.get("picture")
            if isinstance(picture, str) and picture:
                return picture

        return account.get_avatar_url()

    def _baixar_avatar(self, avatar_url):
        if not avatar_url:
            return None, None

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CaronasJP/1.0)",
            "Accept": "image/*,*/*;q=0.8",
        }
        response = requests.get(avatar_url, timeout=10, headers=headers, allow_redirects=True)
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        if not content_type.startswith("image/"):
            return None, None
        return response.content, content_type

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
            avatar_url = self._resolver_avatar_url(sociallogin)
            if avatar_url:
                try:
                    conteudo, content_type = self._baixar_avatar(avatar_url)
                    if not conteudo:
                        return user
                    ext = ".jpg"
                    if "png" in content_type:
                        ext = ".png"
                    filename = f"social_{user.pk}{ext}"
                    user.foto.save(filename, ContentFile(conteudo), save=True)
                except Exception:
                    pass

        return user
