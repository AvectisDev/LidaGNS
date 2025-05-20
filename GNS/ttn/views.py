from django.shortcuts import render, redirect
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.db.models import Q, Sum
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import BalloonTtn
from .forms import BalloonTtnForm


# ТТН для баллонов
class TTNView(generic.ListView):
    model = BalloonTtn
    paginate_by = 10


class TTNDetailView(generic.DetailView):
    model = BalloonTtn


class TTNCreateView(generic.CreateView):
    model = BalloonTtn
    form_class = BalloonTtnForm
    template_name = 'ttn/_equipment_form.html'

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'ТТН {self.object.number} успешно создана')
        return response


class TTNUpdateView(generic.UpdateView):
    model = BalloonTtn
    form_class = BalloonTtnForm
    template_name = 'ttn/_equipment_form.html'

    def get_success_url(self):
        return self.object.get_absolute_url()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'ТТН {self.object.number} успешно обновлена')
        return response


class TTNDeleteView(generic.DeleteView):
    model = BalloonTtn
    success_url = reverse_lazy("ttn:ttn_list")
    template_name = 'ttn/balloonttn_confirm_delete.html'
