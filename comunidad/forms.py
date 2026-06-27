from django import forms
from .models import Habitante
from datetime import datetime

class HabitanteForm(forms.ModelForm):
    class Meta:
        model = Habitante
        fields = [
            'nacionalidad', 'cedula', 'nombres', 'apellidos', 'genero', 
            'fecha_nacimiento','fecha_ingreso', 'calle_sector', 'punto_referencia', 'telefono', 
            'discapacidad', 'parentesco', 'jefe_familia'
        ]
        
        widgets = {
            'nacionalidad': forms.Select(attrs={'class': 'form-select'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00000000'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'genero': forms.Select(attrs={'class': 'form-select'}),
            'fecha_nacimiento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'DD/MM/AAAA',
                'autocomplete': 'off'
            }),
            'fecha_ingreso': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'DD/MM/AAAA',
                'autocomplete': 'off'
            }),
            'calle_sector': forms.Select(attrs={'class': 'form-select'}),
            'punto_referencia': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Ej: Cerca de la bodega de la esquina (Opcional)'}),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: 04141234567'
            }),
            'discapacidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ninguna (opcional)'}),
            'parentesco': forms.Select(attrs={'class': 'form-select'}),
            'jefe_familia': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super(HabitanteForm, self).__init__(*args, **kwargs)
        self.fields['jefe_familia'].queryset = Habitante.objects.filter(parentesco='JEFE')
        self.fields['jefe_familia'].empty_label = "--- Seleccione (Solo si es familiar) ----"
        
        if self.instance and self.instance.fecha_nacimiento:
            self.initial['fecha_nacimiento'] = self.instance.fecha_nacimiento.strftime('%d/%m/%Y')
        if self.instance and self.instance.fecha_ingreso:
            self.initial['fecha_ingreso'] = self.instance.fecha_ingreso.strftime('%d/%m/%Y')

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if telefono:
            num_limpio = telefono.replace('-', '').replace(' ', '').replace('+', '')
            if not num_limpio.isdigit():
                raise forms.ValidationError("El número de teléfono solo debe contener números, espacios, guiones o +.")
        return telefono

    def clean_fecha_nacimiento(self):
        fecha_str = self.cleaned_data.get('fecha_nacimiento')
        if fecha_str:
            # Si ya es un objeto date, devolverlo
            if isinstance(fecha_str, datetime) or hasattr(fecha_str, 'strftime'):
                return fecha_str
            # Si es string, intentar convertir
            if isinstance(fecha_str, str):
                try:
                    return datetime.strptime(fecha_str, '%d/%m/%Y').date()
                except (ValueError, TypeError):
                    raise forms.ValidationError("Formato de fecha inválido. Use DD/MM/AAAA (ejemplo: 15/03/1990)")
        return fecha_str

    def clean_fecha_ingreso(self):
        fecha_str = self.cleaned_data.get('fecha_ingreso')
        if fecha_str:
            # Si ya es un objeto date, devolverlo
            if isinstance(fecha_str, datetime) or hasattr(fecha_str, 'strftime'):
                return fecha_str
            # Si es string, intentar convertir
            if isinstance(fecha_str, str):
                try:
                    return datetime.strptime(fecha_str, '%d/%m/%Y').date()
                except (ValueError, TypeError):
                    raise forms.ValidationError("Formato de fecha inválido. Use DD/MM/AAAA (ejemplo: 15/03/1990)")
        return fecha_str

    def clean(self):
        cleaned_data = super().clean()
        nacimiento = cleaned_data.get("fecha_nacimiento")
        ingreso = cleaned_data.get("fecha_ingreso")
        parentesco = cleaned_data.get("parentesco")
        jefe_familia = cleaned_data.get("jefe_familia")
        cedula = cleaned_data.get("cedula")

        if nacimiento and ingreso and ingreso < nacimiento:
            self.add_error('fecha_ingreso', "La fecha de radicación no puede ser anterior a la fecha de nacimiento.")

        if parentesco == 'JEFE':
            if not cedula or cedula.strip() == '' or cedula.upper() == 'NO POSEE':
                self.add_error('cedula', "Error: Un Jefe de Familia obligatoriamente debe poseer Cédula de Identidad.")

        if parentesco != 'JEFE' and not jefe_familia:
            self.add_error('jefe_familia', "Si no es Jefe de Familia, debe vincularlo a un Jefe existente.")
        
        return cleaned_data
