from django import forms
from .models import Ballon


class Process(forms.Form):
    truck_number = forms.CharField(max_length=15, label="Госномер автомобиля", widget=forms.TextInput(attrs={'placeholder': '1234 AA-1'}))
    phone_number = forms.CharField(max_length=15, label="Номер телефона", widget=forms.TextInput(attrs={'placeholder': '375291112233'}))
    company = forms.CharField(max_length=200, label="Компания")

    def clean_phone_number(self):
        phone_number_data = self.cleaned_data["phone_number"]
        if not phone_number_data.isdigit():
            raise forms.ValidationError("Номер телефона должен состоять только из цифр")
        return phone_number_data


class GetBallonsAmount(forms.Form):
    date = forms.CharField(max_length=10, label="Дата", widget=forms.TextInput(attrs={'placeholder': 'дд.мм.гггг'}))

    def clean_data(self):
        date_data = self.cleaned_data["date"]
        if date_data is None or len(date_data) != 10:
            raise forms.ValidationError("Поле не может быть пустым")
        return date_data
    