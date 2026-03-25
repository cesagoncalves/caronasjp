from django.conf import settings

from usuarios.models import PushSubscription


def push_context(request):
    show_prompt = False
    public_key = settings.VAPID_PUBLIC_KEY or ""
    clear_local_solicitacoes = bool(request.session.pop("clear_local_solicitacoes", False))
    can_enable = False

    if request.user.is_authenticated:
        try:
            has_sub = PushSubscription.objects.filter(user=request.user).exists()
        except Exception:
            has_sub = True
        ask_flag = request.session.get("ask_push_permission", False)
        opt_out = request.session.get("push_prompt_opt_out", False)
        show_prompt = ask_flag and not has_sub and not opt_out
        can_enable = bool(public_key) and not has_sub

    return {
        "PUSH_SHOW_PROMPT": show_prompt,
        "PUSH_PUBLIC_KEY": public_key,
        "CLEAR_LOCAL_SOLICITACOES": clear_local_solicitacoes,
        "PUSH_CAN_ENABLE": can_enable,
    }
