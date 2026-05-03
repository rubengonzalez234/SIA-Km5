from django import forms
from .models import Habitante
class HabitanteForm(forms.ModelForm):
    class Meta:
        model = Habitante
        fields = ['cedula', 'nombres', 'apellidos', 'fecha_nacimiento', 'calle_sector', 'enfermedad_cronica', 'discapacidad']
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'V-00.000.000'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'calle_sector': forms.TextInput(attrs={'class': 'form-control'}),
            'enfermedad_cronica': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'discapacidad': forms.TextInput(attrs={'class': 'form-control'}),
        }


