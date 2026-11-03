"""
WSGI config for focus_cup project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'focus_cup.settings')

application = get_wsgi_application()

# Automatically execute database migrations on application startup
try:
    call_command('migrate', interactive=False)
except Exception as e:
    logging.getLogger(__name__).warning("Startup database migration check note: %s", e)
