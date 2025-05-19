import logging
from celery import shared_task
from django.core.management import call_command


logger = logging.getLogger('filling_station')

@shared_task
def send_to_opc(reader, blink):
    call_command('send_to_opc', reader=reader, blink=blink)
