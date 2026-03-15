"""
WSGI config for caronas_site project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
import traceback

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caronas_site.settings')

if os.getenv("MIGRATE_ON_STARTUP", "").lower() == "true":
    try:
        call_command("migrate", interactive=False)
    except Exception:
        traceback.print_exc(file=sys.stderr)

application = get_wsgi_application()
