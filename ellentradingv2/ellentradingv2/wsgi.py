"""
WSGI config for ellentradingv2 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ellentradingv2.settings')

application = get_wsgi_application()
