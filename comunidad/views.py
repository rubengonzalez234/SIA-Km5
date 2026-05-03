import io
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages  # IMPORTANTE: Para las alertas de error
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

# Librerías para el reporte PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from .models import Habitante
from .forms import HabitanteForm

# --- 1. SECCIÓN DE AUTENTICACIÓN Y ACCESO ---

def login_usuario(request):
    """Maneja el acceso al sistema con redirección por roles."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            
            # Verificación de roles
            es_admin = usuario.is_superuser
            nombres_grupos = list(usuario.groups.values_list('name', flat=True))
            
            if es_admin or "Operador" in nombres_grupos:
                return redirect('lista_habitantes')
            else:
                # Si es un usuario común sin permisos
                messages.error(request, 'Acceso denegado: Tu usuario no tiene permisos de Operador.')
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'comunidad/login.html', {'form': form})

def logout_usuario(request):
    """Cierra la sesión y vuelve a la página pública."""
    logout(request)
    return redirect('home')

def error_403(request, exception=None):
    """Vista personalizada para el error de acceso prohibido."""
    return render(request, '403.html', status=403)


# --- 2. SECCIÓN PÚBLICA / INFORMATIVA ---

def home(request):
    """Página de inicio pública con estadísticas básicas."""
    total_habitantes = Habitante.objects.count()
    return render(request, 'comunidad/home.html', {'total': total_habitantes})


# --- 3. GESTIÓN DE DATOS (CRUD) ---

@login_required(login_url='login')
def lista_habitantes(request):
    """Listado principal con buscador y estadísticas."""
    # Seguridad: Solo SuperAdmin u Operadores
    if not (request.user.is_superuser or request.user.groups.filter(name='Operador').exists()):
        messages.error(request, 'No tienes permiso para ver el listado de habitantes.')
        return redirect('home')

    busqueda = request.GET.get('buscar')
    habitantes = Habitante.objects.all()

    # Cálculos estadísticos
    con_enfermedad = habitantes.exclude(enfermedad_cronica__isnull=True).exclude(enfermedad_cronica="").count()
    con_discapacidad = habitantes.exclude(discapacidad__isnull=True).exclude(discapacidad="").count()

    if busqueda:
        habitantes = habitantes.filter(cedula__icontains=busqueda) | habitantes.filter(nombres__icontains=busqueda)

    context = {
        'habitantes': habitantes,
        'busqueda': busqueda,
        'con_enfermedad': con_enfermedad,
        'con_discapacidad': con_discapacidad,
    }
    return render(request, 'comunidad/lista.html', context)

@login_required(login_url='login')
def crear_habitante(request):
    """Registro de nuevos habitantes (Permitido para Operador y Admin)."""
    if not (request.user.is_superuser or request.user.groups.filter(name='Operador').exists()):
        raise PermissionDenied

    if request.method == 'POST':
        form = HabitanteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Habitante registrado correctamente.')
            return redirect('lista_habitantes')
    else:
        form = HabitanteForm()
    return render(request, 'comunidad/form_habitante.html', {'form': form, 'titulo': 'Registrar Habitante'})

@login_required(login_url='login')
def editar_habitante(request, pk):
    """Edición de datos (Permitido para Operador y Admin)."""
    if not (request.user.is_superuser or request.user.groups.filter(name='Operador').exists()):
        raise PermissionDenied

    habitante = get_object_or_404(Habitante, pk=pk)
    if request.method == 'POST':
        form = HabitanteForm(request.POST, instance=habitante)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos actualizados correctamente.')
            return redirect('lista_habitantes')
    else:
        form = HabitanteForm(instance=habitante)
    return render(request, 'comunidad/form_habitante.html', {'form': form, 'titulo': 'Editar Habitante'})

@login_required(login_url='login')
def eliminar_habitante(request, pk):
    """Eliminación de registros (RESTRICCIÓN CRÍTICA: Solo SuperAdmin)."""
    if not request.user.is_superuser:
        raise PermissionDenied

    habitante = get_object_or_404(Habitante, pk=pk)
    if request.method == 'POST':
        habitante.delete()
        messages.success(request, 'Registro eliminado del sistema.')
        return redirect('lista_habitantes')
    return render(request, 'comunidad/confirmar_eliminar.html', {'habitante': habitante})


# --- 4. SECCIÓN DE REPORTES ---

@login_required(login_url='login')
def exportar_pdf(request):
    """Genera un reporte PDF de los habitantes registrados."""
    if not (request.user.is_superuser or request.user.groups.filter(name='Operador').exists()):
        raise PermissionDenied

    busqueda = request.GET.get('buscar', '')
    habitantes = Habitante.objects.all()
    if busqueda:
        habitantes = habitantes.filter(cedula__icontains=busqueda) | habitantes.filter(nombres__icontains=busqueda)

    # Configuración de respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="reporte_km5_{datetime.now().strftime("%d%m%Y")}.pdf"'
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Encabezado del PDF
    elements.append(Paragraph("REPORTE DE CENSO - COMUNIDAD KM5", styles['Title']))
    elements.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Paragraph("<br/><br/>", styles['Normal']))

    # Estructura de la tabla
    data = [['Cédula', 'Nombre', 'Apellido', 'Calle/Sector']]
    for h in habitantes:
        data.append([h.cedula, h.nombres, h.apellidos, h.calle_sector])

    tabla = Table(data)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ])
    tabla.setStyle(style)
    elements.append(tabla)

    doc.build(elements)
    response.write(buffer.getvalue())
    buffer.close()
    return response