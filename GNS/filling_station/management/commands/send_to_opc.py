import logging
from typing import Any, Dict
from opcua import Client, ua
from django.core.management.base import BaseCommand

logger = logging.getLogger('filling_station')


class Command(BaseCommand):
    help = 'Send data to OPC server'

    def __init__(self):
        super().__init__()
        self.client = Client("opc.tcp://192.168.100.54:4840")

    def add_arguments(self, parser):
        parser.add_argument('--reader', type=int, help='Reader number')
        parser.add_argument('--blink', type=bool, help='Blink status')

    def get_opc_value(self, addr_str):
        """Получить значение с OPC UA сервера по адресу."""
        var = self.client.get_node(addr_str)
        return var.get_value()

    def set_opc_value(self, addr_str, value):
        """Установить значение на OPC UA сервере по адресу."""
        var = self.client.get_node(addr_str)
        return var.set_attribute(ua.AttributeIds.Value, ua.DataValue(value))

    def handle(self, *args: Any, **options: Dict[str, Any]) -> None:
        try:
            self.client.connect()

            reader = options['reader']
            blink = options['blink']

            if blink:
                self.set_opc_value(f'ns=3;s="RFID_LED"."RFID_LED_PULSE"[{reader - 1}]', True)
            else:
                self.set_opc_value(f'ns=3;s="RFID_LED"."RFID_LED_ON"[{reader - 1}]', True)

            logger.info(f'Данные отправлены в OPC: reader-{reader};blink-{blink}')

        except ua.UaError as error:
            logger.error(f'OPC server error: {error}')
        except Exception as error:
            logger.error(f'other error while OPC connection: {error}')
            logger.error(f'reader-{reader}, type of reader-{type(reader)};blink-{blink}, type of blink-{type(blink)}')
        finally:
            self.client.disconnect()
