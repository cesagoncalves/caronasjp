from django.contrib import messages
import json

def modal_messages(request):
    messages_list = []

    for m in messages.get_messages(request):
        level = m.tags if m.tags != "error" else "danger"  # padroniza com bootstrap
        messages_list.append({
            "text": m.message,
            "level": level
        })

    return {
        "messages_json": json.dumps(messages_list)
    }
