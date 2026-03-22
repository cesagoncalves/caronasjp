from django.conf import settings

from usuarios.models import PushSubscription


def push_context(request):
    show_prompt = False
    public_key = settings.VAPID_PUBLIC_KEY or ""

    if request.user.is_authenticated:
        has_sub = PushSubscription.objects.filter(user=request.user).exists()
        ask_flag = request.session.get("ask_push_permission", False)
        show_prompt = ask_flag and not has_sub

    return {
        "PUSH_SHOW_PROMPT": show_prompt,
        "PUSH_PUBLIC_KEY": public_key,
    }
