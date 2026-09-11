"""Celery-задачи filling_station.

OPC-лампа / send_to_opc удалены: индикация RFID идёт через FEIG SET_OUTPUT
(``ReaderSession.indicate_tag_read`` в ``management/commands/rfid_utils``).
"""
