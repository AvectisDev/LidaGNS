from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.paginator import Paginator
from .models import Ballon
from .admin import BallonResources
from .forms import Process, GetBallonsAmount
from datetime import datetime, date, time, timedelta
import locale


# locale.setlocale(locale.LC_TIME, "ru-RU")

def index(request):
    ballons = Ballon.objects.all()
    return render(request, "home.html", {"ballons": ballons})


def client(request):
    ballons = Ballon.objects.all()
    return render(request, "home.html", {"ballons": ballons})


def reader1(request):
    ballons = Ballon.objects.order_by('-id').filter(state = 'Регистрация пустого баллона на складе (цех)')
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    format = '%d.%m.%Y'

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, format)

        dataset = BallonResources().export(Ballon.objects.filter(state = 'Регистрация пустого баллона на складе (цех)', creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_1_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))     
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, format)

    return render(request, "ballons_table.html", {
        "page_obj": page_obj, 
        'ballons_amount': last_date_amount, 
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})

def reader2(request):
    ballons = Ballon.objects.order_by('-id').filter(state = 'Наполнение баллона сжиженным газом')
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    format = '%d.%m.%Y'

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, format)

        dataset = BallonResources().export(Ballon.objects.filter(state = 'Наполнение баллона сжиженным газом', creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_2_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))     
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, format)
    return render(request, "ballons_table.html", {
        "page_obj": page_obj, 
        'ballons_amount': last_date_amount, 
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})

def reader3(request):
    ballons = Ballon.objects.order_by('-id').filter(state = 'Регистрация пустого баллона на складе (рампа)')
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    format = '%d.%m.%Y'

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, format)

        dataset = BallonResources().export(Ballon.objects.filter(state = 'Регистрация пустого баллона на складе (рампа)', creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_3_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))     
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, format)
    return render(request, "ballons_table.html", {
        "page_obj": page_obj, 
        'ballons_amount': last_date_amount, 
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})

def reader4(request):
    ballons = Ballon.objects.order_by('-id').filter(state = 'Регистрация полного баллона на складе')
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    format = '%d.%m.%Y'

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, format)

        dataset = BallonResources().export(Ballon.objects.filter(state = 'Регистрация полного баллона на складе', creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_4_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))     
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, format)
    return render(request, "ballons_table.html", {
        "page_obj": page_obj, 
        'ballons_amount': last_date_amount, 
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})

def reader5(request):
    ballons = Ballon.objects.order_by('-id').filter(state = 'Погрузка полного баллона на тралл 2')
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    format = '%d.%m.%Y'

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, format)

        dataset = BallonResources().export(Ballon.objects.filter(state = 'Погрузка полного баллона на тралл 2', creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_5_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))     
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, format)
    return render(request, "ballons_table.html", {
        "page_obj": page_obj, 
        'ballons_amount': last_date_amount, 
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})

def reader6(request):
    ballons = Ballon.objects.order_by('-id').filter(state = 'Погрузка полного баллона на тралл 1')
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    format = '%d.%m.%Y'

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, format)

        dataset = BallonResources().export(Ballon.objects.filter(state = 'Погрузка полного баллона на тралл 1', creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_6_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))     
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, format)
    return render(request, "ballons_table.html", {
        "page_obj": page_obj, 
        'ballons_amount': last_date_amount, 
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})

def reader7(request):
    ballons = Ballon.objects.order_by('-id').filter(state = 'Погрузка полного баллона в кассету')
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    format = '%d.%m.%Y'

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, format)

        dataset = BallonResources().export(Ballon.objects.filter(state = 'Погрузка полного баллона в кассету', creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_7_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))     
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, format)
    return render(request, "ballons_table.html", {
        "page_obj": page_obj, 
        'ballons_amount': last_date_amount, 
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})

def reader8(request):
    ballons = Ballon.objects.order_by('-id').filter(state = 'Регистрация пустого баллона на складе (из кассеты)')
    paginator = Paginator(ballons, 15)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)

    format = '%d.%m.%Y'

    date_process = GetBallonsAmount()
    if request.method == "POST":
        required_date = request.POST.get("date")
        format_required_date = datetime.strptime(required_date, format)

        dataset = BallonResources().export(Ballon.objects.filter(state = 'Регистрация пустого баллона на складе (из кассеты)', creation_date = format_required_date))
        response = HttpResponse(dataset.xls, content_type='xls')
        response['Content-Disposition'] = f'attachment; filename="RFID_8_{datetime.strftime(format_required_date, '%Y.%m.%d')}.xls"'
        return response
    else:
        date_process = GetBallonsAmount()
        format_required_date = datetime.today()

    last_date_amount = len(ballons.filter(creation_date = datetime.today()))
    previous_date_amount = len(ballons.filter(creation_date = datetime.today() - timedelta(days=1)))     
    required_date_amount = len(ballons.filter(creation_date = format_required_date))

    view_required_data = datetime.strftime(format_required_date, format)
    return render(request, "ballons_table.html", {
        "page_obj": page_obj, 
        'ballons_amount': last_date_amount, 
        'previous_ballons_amount': previous_date_amount,
        'required_date_amount': required_date_amount,
        'format_required_date': view_required_data,
        'form': date_process})
