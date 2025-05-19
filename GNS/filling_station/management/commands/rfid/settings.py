READER_LIST = [{} for i in range(12)]

# Считыватели на отгрузке
# 1-й дальний от цеха
READER_LIST[0] = {
    'ip': '192.168.100.61',
    'port': 10001,
    'number': 1,
    'status': 'Погрузка полного баллона на трал 1',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': 'unloading'
}

# 2-й ближе к цеху
READER_LIST[1] = {
    'ip': '192.168.100.62',
    'port': 10001,
    'number': 2,
    'status': 'Погрузка полного баллона на трал 2',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': 'unloading'
}

# Считыватели на приёмке
# 3-й дальний от цеха
READER_LIST[2] = {
    'ip': '192.168.100.63',
    'port': 10001,
    'number': 3,
    'status': 'Приёмка пустого баллона из трала 1',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': 'loading'
}

# 4-й ближе к цеху
READER_LIST[3] = {
    'ip': '192.168.100.64',
    'port': 10001,
    'number': 4,
    'status': 'Приёмка пустого баллона из трала 2',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': 'loading'
}

# Выход из наполнительного цеха
READER_LIST[4] = {
    'ip': '192.168.100.65',
    'port': 10001,
    'number': 5,
    'status': 'Регистрация полного баллона на складе',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': None
}

# Вход в наполнительный цех
READER_LIST[5] = {
    'ip': '192.168.100.66',
    'port': 10001,
    'number': 6,
    'status': 'Регистрация пустого баллона в цеху',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': None
}

# Считыватели в цеху
# Карусель №1
READER_LIST[6] = {
    'ip': '192.168.100.67',
    'port': 10001,
    'number': 7,
    'status': 'Наполнение баллона сжиженным газом. Карусель №1',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': None
}

# Карусель №2
READER_LIST[7] = {
    'ip': '192.168.100.68',
    'port': 10001,
    'number': 8,
    'status': 'Наполнение баллона сжиженным газом. Карусель №2',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': None
}

#
READER_LIST[8] = {
    'ip': '192.168.100.69',
    'port': 10001,
    'number': 9,
    'status': 'Вход в наполнительный цех из ремонтного',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': None
}

#
READER_LIST[9] = {
    'ip': '192.168.100.70',
    'port': 10001,
    'number': 10,
    'status': 'Выход из наполнительного цеха в ремонтный',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': None
}

#
READER_LIST[10] = {
    'ip': '192.168.100.71',
    'port': 10001,
    'number': 11,
    'status': 'Вход в ремонтный цех из наполнительного',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': None
}

#
READER_LIST[11] = {
    'ip': '192.168.100.72',
    'port': 10001,
    'number': 12,
    'status': 'Выход из ремонтного цеха в наполнительный',
    'input_state': 0,
    'previous_nfc_tags': [],
    'function': None
}

# Команды, посылаемые на считыватель
COMMANDS = {
    'host_read': '020009ffb001001843',
    'read_complete': '02000DFF72010181010019236B',  # зажигаем зелёную лампу на считывателе на 2.5 сек
    'read_complete_with_error': '02000DFF720101810B0014BCC3',  # мигание зелёной лампы на считывателе 2 сек
    'buffer_read': '020009FFB02B005B9D',  # чтение буферной памяти
    'inputs_read': '020007FF746660',  # чтение состояния входов
    'all_buffer_read': '02000AFF2B0000FF89EB',  # чтение всего буфера
    'read_last_item_from_buffer': '02000AFF2B00FFFF4914',
    'clean_buffer': '020007FF325447'  # команда очистки буфера
}
# 02 00 08 FF B0 84 4F DB   Reader: RF-Warning - если нет данных с ридера
