import os

from django.core.asgi import get_asgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GNS.settings')

application = get_asgi_application()

# Запуск команды выполнения программы обработки RFID меток
# call_command('run_scripts')
