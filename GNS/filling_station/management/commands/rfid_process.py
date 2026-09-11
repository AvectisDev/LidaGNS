import os
import subprocess
import sys
from pathlib import Path

from django.core.management.base import BaseCommand


DJANGO_PROJECT_DIR = Path(__file__).resolve().parents[3]


class Command(BaseCommand):
    help = 'Запуск Notification Mode сервера RFID-считывателей'

    def handle(self, *args, **kwargs):
        env = os.environ.copy()
        subprocess.Popen(
            [
                sys.executable,
                '-m',
                'filling_station.management.commands.rfid_utils.feig_protocol',
            ],
            env=env,
            cwd=DJANGO_PROJECT_DIR,
        )
