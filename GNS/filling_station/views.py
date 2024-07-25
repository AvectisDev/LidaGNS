from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.core import serializers
from django.core.paginator import Paginator
from .models import Ballon
from .admin import BallonResources
from .forms import Process, GetBallonsAmount
from datetime import datetime, date, time, timedelta
from django.views.decorators.csrf import csrf_exempt
import json
import locale


# locale.setlocale(locale.LC_TIME, "ru-RU")

def index(request):
    ballons = Ballon.objects.all()
    return render(request, "home.html", {"ballons": ballons})


def client(request):
    ballons = Ballon.objects.all()
    return render(request, "home.html", {"ballons": ballons})


def apiGetBallonPassport(request):
    nfc = request.GET.get("nfc", 0)
    balloons = Ballon.objects.order_by('-id').filter(nfc_tag = nfc)
    # serialized_queryset = serializers.serialize('json', balloon)
    return JsonResponse({
        'nfc_tag':balloons[0].nfc_tag,
        'serial_number':balloons[0].serial_number,
        'creation_date':balloons[0].creation_date,
        'capacity':balloons[0].capacity,
        'empty_weight':balloons[0].empty_weight,
        'full_weight':balloons[0].full_weight,
        'current_examination_date':balloons[0].current_examination_date,
        'next_examination_date':balloons[0].next_examination_date,
        'state':balloons[0].state})


@csrf_exempt
def apiUpdateBallonPassport(request):
    try:
        data = json.loads(request.body)
        nfc = data.get("nfc_tag")
        balloon = Ballon.objects.filter(nfc_tag=nfc).first()

        if not balloon:
            return JsonResponse({'error': 'Balloon not found'}, status=404)

        balloon.serial_number = data.get('serial_number', balloon.serial_number)
        balloon.creation_date = data.get('creation_date', balloon.creation_date)
        balloon.capacity = data.get('capacity', balloon.capacity)
        balloon.empty_weight = data.get('empty_weight', balloon.empty_weight)
        balloon.full_weight = data.get('full_weight', balloon.full_weight)
        balloon.current_examination_date = data.get('current_examination_date', balloon.current_examination_date)
        balloon.next_examination_date = data.get('next_examination_date', balloon.next_examination_date)
        balloon.state = data.get('state', balloon.state)

        # Save the updated object to the database
        balloon.save()

        return JsonResponse({
            'nfc_tag':balloon.nfc_tag,
            'serial_number':balloon.serial_number,
            'creation_date':balloon.creation_date,
            'capacity':balloon.capacity,
            'empty_weight':balloon.empty_weight,
            'full_weight':balloon.full_weight,
            'current_examination_date':balloon.current_examination_date,
            'next_examination_date':balloon.next_examination_date,
            'state':balloon.state})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    return JsonResponse({'error': 'Invalid HTTP method'}, status=405)


def reader_info(request, reader = '1'):

    if reader == '1':
        status = 'Погрузка полного баллона на тралл 1 (RFID №1)'
    elif reader == '2':
        status = 'Погрузка полного баллона на тралл 2 (RFID №2)'
    elif reader == '3':
        status = 'Приёмка пустого баллона из тралла 1 (RFID №3)'
    elif reader == '4':
        status = 'Приёмка пустого баллона из тралла 2 (RFID №4)'
    elif reader == '5':
        status = 'Регистрация полного баллона на складе (RFID №5)'
    elif reader == '6':
        status = 'Регистрация пустого баллона в цеху (RFID №6)'
    elif reader == '7':
        status = 'Наполнение баллона сжиженным газом. Карусель №1 (RFID №7)'
    elif reader == '8':
        status = 'Наполнение баллона сжиженным газом. Карусель №2 (RFID №8)'
    elif reader == '9':
        status = 'Вход в наполнительный цех из ремонтного (RFID №9)'
    elif reader == '10':
        status = 'Выход из наполнительного цеха в ремонтный (RFID №10)'
    elif reader == '11':
        status = 'Вход в ремонтный цех из наполнительного (RFID №11)'
    elif reader == '12':
        status = 'Выход из ремонтного цеха в наполнительный (RFID №12)'

    ballons = Ballon.objects.order_by('-id').filter(state = status)
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, '%d.%m.%Y')

        dataset = BallonResources().export(Ballon.objects.filter(state = status, creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_1_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, '%d.%m.%Y')

    return render(request, "ballons_table.html", {
        "page_obj": page_obj,
        'ballons_amount': last_date_amount,
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})