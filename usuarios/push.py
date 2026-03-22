import json
from django.conf import settings
from pywebpush import webpush, WebPushException

from usuarios.models import PushSubscription


def send_push_to_user(user, title, body, url="/"):
    if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
        return 0

    subs = PushSubscription.objects.filter(user=user)
    if not subs.exists():
        return 0

    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "url": url,
        }
    )

    sent = 0
    for sub in subs:
        subscription_info = {
            "endpoint": sub.endpoint,
            "keys": {
                "p256dh": sub.p256dh,
                "auth": sub.auth,
            },
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
            sent += 1
        except WebPushException:
            sub.delete()

    return sent
