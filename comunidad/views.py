import os
import fitz  # PyMuPDF
from PIL import Image
from django.conf import settings
from django.contrib.staticfiles import finders
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.template.loader import get_template
from django.template.loader import render_to_string 
from django.utils import timezone
from xhtml2pdf import pisa
from django.db.models import Case, When, Value, IntegerField, F
from django.http import HttpResponse, JsonResponse
import io
from django.db.models import Q, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Proyecto, NotaSeguimiento
import json
#FINANZAS
from .models import Voceria, MovimientoFinanciero
# --- IMPORTACIONES COMUNALES SINCRO-EXTENDIDAS ---
# Línea 17 de tu views.py original corregida:
from .models import Habitante, Voceria, CensoBombona, Proyecto, NotaSeguimiento,  ContadorConstancia
from .forms import HabitanteForm
def generar_pdf_con_marca(html_content, filename, mostrar_en_navegador=True, tamaño_marca=0.6, opacidad_marca=0.3):
    """
    Genera un PDF a partir de HTML y le añade una marca de agua.
    
    Args:
        html_content: String con el contenido HTML a convertir
        filename: Nombre del archivo PDF (sin extensión)
        mostrar_en_navegador: True para inline, False para descarga
        tamaño_marca: 0.0 a 1.0 (porcentaje de la página)
        opacidad_marca: 0.0 a 1.0 (transparencia)
    
    Returns:
        HttpResponse con el PDF listo para mostrar/descargar
    """
    try:
        # 1. Generar el PDF temporal en memoria
        pdf_buffer = io.BytesIO()
        
        pisa_status = pisa.CreatePDF(
            io.BytesIO(html_content.encode("utf-8")),
            dest=pdf_buffer,
            link_callback=link_callback
        )
        
        if pisa_status.err:
            return HttpResponse(f"Error al generar el PDF: {pisa_status.err}", status=500)
        
        # 2. Si no hay error, añadir la marca de agua
        pdf_buffer.seek(0)  # Volver al inicio del buffer
        
        # 3. Abrir el PDF con PyMuPDF
        pdf_document = fitz.open(stream=pdf_buffer, filetype="pdf")
        
        # 4. Cargar la imagen de marca de agua desde static
        marca_path = finders.find('img/logocomunas.png')
        if not marca_path:
            # Si no se encuentra con finders, intentar con ruta directa
            marca_path = os.path.join(settings.STATIC_ROOT, 'img', 'logocomunas.png')
            if not os.path.exists(marca_path):
                # Fallback: buscar en STATICFILES_DIRS
                for static_dir in settings.STATICFILES_DIRS:
                    test_path = os.path.join(static_dir, 'img', 'logocomunas.png')
                    if os.path.exists(test_path):
                        marca_path = test_path
                        break
        
        if marca_path and os.path.exists(marca_path):
            # Procesar la imagen con PIL para transparencia
            img = Image.open(marca_path)
            
            # Convertir a RGBA si no lo es
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Aplicar opacidad
            data = list(img.getdata())
            new_data = []
            for r, g, b, a in data:
                new_data.append((r, g, b, int(a * opacidad_marca)))
            img.putdata(new_data)
            
            # Guardar imagen en memoria
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            
            # Obtener dimensiones de la primera página
            primera_pagina = pdf_document[0]
            rect = primera_pagina.rect
            
            # Procesar cada página
            for pagina_num in range(len(pdf_document)):
                pagina = pdf_document[pagina_num]
                
                # Calcular tamaño y posición centrada
                ancho_imagen = rect.width * tamaño_marca
                alto_imagen = rect.height * tamaño_marca
                
                x = (rect.width - ancho_imagen) / 2
                y = (rect.height - alto_imagen) / 2
                
                rect_imagen = fitz.Rect(x, y, x + ancho_imagen, y + alto_imagen)
                
                # Insertar imagen
                pagina.insert_image(rect_imagen, stream=img_data, keep_proportion=True)
                
                print(f"✅ Marca de agua añadida en página {pagina_num + 1}")
        else:
            print("⚠️ No se encontró la imagen de marca de agua. Se genera PDF sin marca.")
        
        # 5. Guardar el PDF final en un nuevo buffer
        output_buffer = io.BytesIO()
        pdf_document.save(output_buffer)
        pdf_document.close()
        
        # 6. Preparar la respuesta HTTP
        response = HttpResponse(output_buffer.getvalue(), content_type='application/pdf')
        
        if mostrar_en_navegador:
            response['Content-Disposition'] = f'inline; filename="{filename}.pdf"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        
        return response
        
    except ImportError as e:
        return HttpResponse(f"Error: Falta una dependencia. Instala PyMuPDF y Pillow. {str(e)}", status=500)
    except Exception as e:
        return HttpResponse(f"Error al generar el PDF con marca de agua: {str(e)}", status=500)


# ====================================================================================
# FUNCIÓN AUXILIAR PARA OBTENER LA RUTA DE LA MARCA DE AGUA
# ====================================================================================
def obtener_ruta_marca_agua():
    """
    Obtiene la ruta de la imagen de marca de agua desde el directorio static
    """
    # Buscar en los directorios de static
    posibles_rutas = [
        finders.find('img/logocomunas.png'),
        os.path.join(settings.STATIC_ROOT, 'img', 'logocomunas.png'),
        os.path.join(settings.BASE_DIR, 'static', 'img', 'logocomunas.png'),
    ]
    
    # También buscar en STATICFILES_DIRS
    if hasattr(settings, 'STATICFILES_DIRS'):
        for static_dir in settings.STATICFILES_DIRS:
            test_path = os.path.join(static_dir, 'img', 'logocomunas.png')
            if os.path.exists(test_path):
                posibles_rutas.append(test_path)
    
    for ruta in posibles_rutas:
        if ruta and os.path.exists(ruta):
            return ruta
    
    return None

# ====================================================================================
# FUNCIÓN AUXILIAR PARA OBTENER NOMBRE DEL MES EN ESPAÑOL
# ====================================================================================
def obtener_nombre_mes(numero_mes):
    """
    Convierte un número de mes (1-12) a su nombre en español en minúscula.
    Ejemplo: 1 -> "enero", 12 -> "diciembre"
    """
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    if 1 <= numero_mes <= 12:
        return meses[numero_mes - 1]
    return ""
    # ====================================================================================
# --- 1. SECCIÓN DE AUTENTICACIÓN Y ACCESO ---
# ====================================================================================

def login_usuario(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            
            es_admin = usuario.is_superuser
            es_operador = usuario.groups.filter(name="Operador").exists()
            
            if es_admin or es_operador:
                return redirect('lista_habitantes')
            else:
                logout(request)
                messages.error(request, "Acceso denegado: Su cuenta no posee el rol de Operador ni Administrador.")
                return redirect('login')
        else:
            messages.error(request, "Usuario o contraseña incorrectos. Por favor, intente de nuevo.")
    else:
        form = AuthenticationForm()
    return render(request, 'comunidad/login.html', {'form': form})


def logout_usuario(request):
    logout(request)
    messages.info(request, "Ha cerrado sesión de forma segura.")
    return redirect('login')


# ====================================================================================
# --- 2. SISTEMA DE CONTROL DE HABITANTES (CENSO / CRUD) ---
# ====================================================================================
@login_required(login_url='login')
def lista_habitantes(request):
    # 1. Base de datos completa
    habitantes_base = Habitante.objects.all()

    ver = request.GET.get('ver', 'todos')
    etapa = request.GET.get('etapa', '')
    busqueda = request.GET.get('buscar', '').strip()
    calle_filtro = request.GET.get('calle', '').strip()  # Para el PDF por calle

    # ============================================================
    # FILTRO DE BÚSQUEDA
    # ============================================================
    if busqueda:
        if busqueda.upper() == "NO POSEE":
            habitantes_base = habitantes_base.filter(Q(cedula__isnull=True) | Q(cedula=''))
        else:
            palabras = busqueda.split()
            filtro_nombre_apellido = Q()
            for palabra in palabras:
                filtro_nombre_apellido &= (Q(nombres__icontains=palabra) | Q(apellidos__icontains=palabra))
            habitantes_base = habitantes_base.filter(filtro_nombre_apellido | Q(cedula__icontains=busqueda))

    # ============================================================
    # FILTRO POR CALLE (para PDF por calle)
    # ============================================================
    if calle_filtro:
        habitantes_base = habitantes_base.filter(calle_sector=calle_filtro)

    # ============================================================
    # FILTRO POR ETAPA DE VIDA
    # ============================================================
    habitantes_validos = []
    for h in habitantes_base:
        cumple_etapa = True
        edad_habitante = h.edad
        genero_upper = str(h.genero).upper() if h.genero else ''
        es_mujer = genero_upper in ['F', 'FEMENINO', 'MUJER']

        if es_mujer:
            if edad_habitante <= 12:
                etapa_actual = 'Niño(a)'
            elif 13 <= edad_habitante <= 17:
                etapa_actual = 'Adolescente'
            elif 18 <= edad_habitante <= 54:
                etapa_actual = 'Adulto(a)'
            else:
                etapa_actual = 'Adulto(a) Mayor'
        else:
            if edad_habitante <= 12:
                etapa_actual = 'Niño(a)'
            elif 13 <= edad_habitante <= 17:
                etapa_actual = 'Adolescente'
            elif 18 <= edad_habitante <= 59:
                etapa_actual = 'Adulto(a)'
            else:
                etapa_actual = 'Adulto(a) Mayor'
            
        if etapa == 'nino' and etapa_actual != 'Niño(a)':
            cumple_etapa = False
        elif etapa == 'adolescente' and etapa_actual != 'Adolescente':
            cumple_etapa = False
        elif etapa == 'adulto' and etapa_actual != 'Adulto(a)':
            cumple_etapa = False
        elif etapa == 'mayor' and etapa_actual != 'Adulto(a) Mayor':
            cumple_etapa = False
        
        if cumple_etapa:
            h.etapa_vida_texto = etapa_actual
            habitantes_validos.append(h)

    # ============================================================
    # FILTRO POR "JEFES DE FAMILIA" (SOLO JEFES)
    # ============================================================
    if ver == 'jefes':
        habitantes_validos = [h for h in habitantes_validos if h.parentesco == 'JEFE']

    # ============================================================
    # ORDENAMIENTO JERÁRQUICO (Jefe -> Miembros) PARA LA TABLA PLANA
    # ============================================================
    habitantes_ordenados = []

    if ver == 'jefes':
        # Ya están filtrados solo jefes
        habitantes_ordenados = habitantes_validos
    else:
        jefes = [h for h in habitantes_validos if h.parentesco == 'JEFE']
        miembros = [h for h in habitantes_validos if h.parentesco != 'JEFE']

        for jefe in jefes:
            habitantes_ordenados.append(jefe)
            miembros_del_jefe = Habitante.objects.filter(jefe_familia=jefe).exclude(parentesco='JEFE')
            
            if busqueda or etapa:
                miembros_del_jefe = [m for m in miembros if m.jefe_familia_id == jefe.id]
            
            for miembro in miembros_del_jefe:
                if miembro not in habitantes_ordenados:
                    habitantes_ordenados.append(miembro)
        
        for miembro in miembros:
            if miembro not in habitantes_ordenados:
                habitantes_ordenados.append(miembro)

    # ============================================================
    # DATOS PARA LOS ACORDEONES POR SECTOR
    # ============================================================
    # TODOS los habitantes por sector (para Núcleo Familiar)
    calle_monjas_i = Habitante.objects.filter(calle_sector='Monjas I')
    calle_monjas_ii = Habitante.objects.filter(calle_sector='Monjas II')
    calle_club_sucre = Habitante.objects.filter(calle_sector='Vía club Sucre')
    calle_entrada_km5 = Habitante.objects.filter(calle_sector='Entrada Km5 vía la amistad')

    # SOLO JEFES por sector (para Jefes de Familia)
    calle_monjas_i_jefes = Habitante.objects.filter(calle_sector='Monjas I', parentesco='JEFE')
    calle_monjas_ii_jefes = Habitante.objects.filter(calle_sector='Monjas II', parentesco='JEFE')
    calle_club_sucre_jefes = Habitante.objects.filter(calle_sector='Vía club Sucre', parentesco='JEFE')
    calle_entrada_km5_jefes = Habitante.objects.filter(calle_sector='Entrada Km5 vía la amistad', parentesco='JEFE')

    # Si hay búsqueda, filtramos los acordeones
    if busqueda:
        calle_monjas_i = calle_monjas_i.filter(
            Q(nombres__icontains=busqueda) | Q(apellidos__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )
        calle_monjas_ii = calle_monjas_ii.filter(
            Q(nombres__icontains=busqueda) | Q(apellidos__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )
        calle_club_sucre = calle_club_sucre.filter(
            Q(nombres__icontains=busqueda) | Q(apellidos__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )
        calle_entrada_km5 = calle_entrada_km5.filter(
            Q(nombres__icontains=busqueda) | Q(apellidos__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )
        
        calle_monjas_i_jefes = calle_monjas_i_jefes.filter(
            Q(nombres__icontains=busqueda) | Q(apellidos__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )
        calle_monjas_ii_jefes = calle_monjas_ii_jefes.filter(
            Q(nombres__icontains=busqueda) | Q(apellidos__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )
        calle_club_sucre_jefes = calle_club_sucre_jefes.filter(
            Q(nombres__icontains=busqueda) | Q(apellidos__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )
        calle_entrada_km5_jefes = calle_entrada_km5_jefes.filter(
            Q(nombres__icontains=busqueda) | Q(apellidos__icontains=busqueda) | Q(cedula__icontains=busqueda)
        )

    # Si el filtro es "jefes", los acordeones deben mostrar SOLO jefes
    if ver == 'jefes':
        calle_monjas_i = calle_monjas_i.filter(parentesco='JEFE')
        calle_monjas_ii = calle_monjas_ii.filter(parentesco='JEFE')
        calle_club_sucre = calle_club_sucre.filter(parentesco='JEFE')
        calle_entrada_km5 = calle_entrada_km5.filter(parentesco='JEFE')

    # ============================================================
    # CONTADORES PARA LOS BOTONES DE ETAPA
    # ============================================================
    todos_los_habitantes = Habitante.objects.all()
    count_ninos = 0
    count_adolescentes = 0
    count_adultos = 0
    count_mayores = 0

    for h in todos_los_habitantes:
        e = h.edad
        g_upper = str(h.genero).upper() if h.genero else ''
        es_m = g_upper in ['F', 'FEMENINO', 'MUJER']
        
        if es_m:
            if e <= 12:
                count_ninos += 1
            elif 13 <= e <= 17:
                count_adolescentes += 1
            elif 18 <= e <= 54:
                count_adultos += 1
            else:
                count_mayores += 1
        else:
            if e <= 12:
                count_ninos += 1
            elif 13 <= e <= 17:
                count_adolescentes += 1
            elif 18 <= e <= 59:
                count_adultos += 1
            else:
                count_mayores += 1

    # ============================================================
    # CONTEXTO FINAL
    # ============================================================
    contexto = {
        'habitantes': habitantes_ordenados,
        'calle_monjas_i': calle_monjas_i,
        'calle_monjas_ii': calle_monjas_ii,
        'calle_club_sucre': calle_club_sucre,
        'calle_entrada_km5': calle_entrada_km5,
        'calle_monjas_i_jefes': calle_monjas_i_jefes,
        'calle_monjas_ii_jefes': calle_monjas_ii_jefes,
        'calle_club_sucre_jefes': calle_club_sucre_jefes,
        'calle_entrada_km5_jefes': calle_entrada_km5_jefes,
        'busqueda': busqueda,
        'ver': ver,
        'etapa': etapa,
        'count_ninos': count_ninos,
        'count_adolescentes': count_adolescentes,
        'count_adultos': count_adultos,
        'count_mayores': count_mayores,
    }
    
    return render(request, 'comunidad/lista.html', contexto)

# ====================================================================================
# --- CREAR HABITANTE ---
# ====================================================================================
@login_required(login_url='login')
def crear_habitante(request):
    if request.method == 'POST':
        data = request.POST.copy()
        cedula_ingresada = data.get('cedula', '').strip()
        parentesco = data.get('parentesco', '')
        es_promocion = data.get('promocion_habilitada') == 'true'

        # Caso 1: Sin cédula o "NO POSEE"
        if not cedula_ingresada or cedula_ingresada == "NO POSEE":
            data['cedula'] = ''
            form = HabitanteForm(data)
            if form.is_valid():
                form.save()
                messages.success(request, "Habitante registrado con éxito.")
                return redirect('lista_habitantes')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"Error en '{field}': {error}")
                return render(request, 'comunidad/form_habitante.html', {'form': form, 'titulo': 'Registrar Habitante'})

        # Caso 2: La cédula YA EXISTE
        habitante_existente = Habitante.objects.filter(cedula=cedula_ingresada).first()
        
        if habitante_existente:
            if parentesco == 'JEFE':
                if habitante_existente.parentesco == 'JEFE' and not es_promocion:
                    # ENVIAR MENSAJE DE ERROR Y VOLVER AL FORMULARIO
                    messages.error(request, f"Error! La cédula ingresada ya está registrada como jefe de familia.")
                    form = HabitanteForm(data)
                    return render(request, 'comunidad/form_habitante.html', {'form': form, 'titulo': 'Registrar Habitante'})
                
                # Actualizar parentesco y desvincular (promoción)
                habitante_existente.parentesco = 'JEFE'
                habitante_existente.jefe_familia = None
                
                # Actualizar datos de contacto (vienen del modal)
                if 'calle_sector' in data and data['calle_sector']:
                    habitante_existente.calle_sector = data['calle_sector']
                if 'telefono' in data:
                    habitante_existente.telefono = data['telefono']
                if 'punto_referencia' in data:
                    habitante_existente.punto_referencia = data['punto_referencia']
                
                habitante_existente.save()
                messages.success(request, f"{habitante_existente.nombres} {habitante_existente.apellidos} ahora es Jefe de Familia.")
                return redirect('lista_habitantes')
            else:
                messages.error(request, f"⚠️ Ya existe un ciudadano registrado con la Cédula N° {cedula_ingresada}.")
                form = HabitanteForm(data)
                return render(request, 'comunidad/form_habitante.html', {'form': form, 'titulo': 'Registrar Habitante'})
        
        # Caso 3: Cédula NO existe
        else:
            form = HabitanteForm(data)
            if form.is_valid():
                form.save()
                messages.success(request, "Habitante registrado con éxito.")
                return redirect('lista_habitantes')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"❌ Error en '{field}': {error}")
                return render(request, 'comunidad/form_habitante.html', {'form': form, 'titulo': 'Registrar Habitante'})

    else:
        form = HabitanteForm()

    return render(request, 'comunidad/form_habitante.html', {'form': form, 'titulo': 'Registrar Habitante'})

def editar_habitante(request, pk):
    habitante = get_object_or_404(Habitante, pk=pk)
    if request.method == 'POST':
        data = request.POST.copy()
        parentesco = data.get('parentesco', '')
        cedula_ingresada = data.get('cedula', '').strip()

        if parentesco == 'JEFE':
            data['jefe_familia'] = ''
        if not cedula_ingresada or cedula_ingresada == "NO POSEE":
            data['cedula'] = ''

        form = HabitanteForm(data, instance=habitante)
        if form.is_valid():
            instancia = form.save(commit=False)
            if parentesco == 'JEFE':
                instancia.jefe_familia = None
            if not data['cedula']:
                instancia.cedula = None
            instancia.save()
            messages.success(request, f"El registro de {habitante.nombres} se actualizó correctamente.")
            return redirect('lista_habitantes')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error al actualizar: {error}")
    else:
        form = HabitanteForm(instance=habitante)
    return render(request, 'comunidad/form_habitante.html', {'form': form, 'titulo': 'Editar Habitante', 'h': habitante})

@login_required(login_url='login')
def eliminar_habitante(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied("No posee privilegios necesarios.")
        
    habitante = get_object_or_404(Habitante, pk=pk)
    
    if request.method == 'POST':
        nombre_guardado = f"{habitante.nombres} {habitante.apellidos}"
        
        if habitante.parentesco == 'JEFE':
            familiares_asociados = Habitante.objects.filter(jefe_familia=habitante)
            total_familiares = familiares_asociados.count()
            
            if total_familiares > 0:
                familiares_asociados.delete()
                messages.warning(request, f"Se eliminó al Jefe de Familia '{nombre_guardado}' y a sus {total_familiares} miembros asociados.")
            else:
                messages.success(request, f"El ciudadano(a) {nombre_guardado} ha sido removido.")
        else:
            messages.success(request, f"El ciudadano(a) {nombre_guardado} ha sido removido.")
            
        habitante.delete()
        return redirect('lista_habitantes')
        
    return render(request, 'comunidad/confirmar_eliminar.html', {'habitante': habitante})


# ====================================================================================
# --- 3. SECCIÓN DE REPORTES (EXPORTACIÓN A PDF) ---
# ====================================================================================
@login_required(login_url='login')
def exportar_censo_pdf(request):
    # Obtener parámetros de filtrado
    busqueda = request.GET.get('buscar', '')
    ver = request.GET.get('ver', 'todos')
    etapa = request.GET.get('etapa', '')
    sector = request.GET.get('sector', '')
    calle = request.GET.get('calle', '')
    
    # SI SE FILTRA POR CALLE, FORZAMOS ver='todos' para mostrar TODOS los habitantes
    if calle:
        ver = 'todos'
        sector = calle
    
    # Obtener todos los habitantes
    habitantes = Habitante.objects.all()
    
    # Filtrar por sector
    if sector:
        sector_clean = sector.strip()
        habitantes = habitantes.filter(calle_sector=sector_clean)
    
    # Filtrar por búsqueda
    if busqueda:
        if busqueda.upper() == "NO POSEE":
            habitantes = habitantes.filter(Q(cedula__isnull=True) | Q(cedula__exact=''))
        else:
            habitantes = habitantes.filter(
                Q(nombres__icontains=busqueda) | 
                Q(apellidos__icontains=busqueda) | 
                Q(cedula__icontains=busqueda)
            )
    
    # Filtrar por jefes de familia SOLO si NO hay filtro de sector
    if ver == 'jefes' and not sector:
        habitantes = habitantes.filter(parentesco='JEFE')
    
    # ============================================================
    # FILTRAR POR ETAPA DE EDAD (CORREGIDO CON GÉNERO)
    # ============================================================
    if etapa and not sector:
        habitantes_filtrados = []
        for h in habitantes:
            genero_upper = str(h.genero).upper() if h.genero else ''
            es_mujer = genero_upper in ['F', 'FEMENINO', 'MUJER']
            edad = h.edad
            
            if etapa == 'nino':
                if edad <= 12:
                    habitantes_filtrados.append(h)
            
            elif etapa == 'adolescente':
                if 13 <= edad <= 17:
                    habitantes_filtrados.append(h)
            
            elif etapa == 'adulto':
                if es_mujer:
                    # MUJERES: Adultas de 18 a 54 años
                    if 18 <= edad <= 54:
                        habitantes_filtrados.append(h)
                else:
                    # HOMBRES: Adultos de 18 a 59 años
                    if 18 <= edad <= 59:
                        habitantes_filtrados.append(h)
            
            elif etapa == 'mayor':
                if es_mujer:
                    # MUJERES: Adultas Mayores desde 55 años
                    if edad >= 55:
                        habitantes_filtrados.append(h)
                else:
                    # HOMBRES: Adultos Mayores desde 60 años
                    if edad >= 60:
                        habitantes_filtrados.append(h)
        
        habitantes = habitantes_filtrados
    
    # ORDENAR: JEFES primero, luego familiares (siempre)
    orden_parentesco = {
        'JEFE': 0,
        'ESPOSO': 1,
        'ESPOSA': 1,
        'CONYUGE': 1,
        'HIJO': 2,
        'HIJA': 2,
        'NIETO': 3,
        'NIETA': 3,
        'PADRE': 4,
        'MADRE': 4,
        'SUEGRO': 5,
        'SUEGRA': 5,
        'HERMANO': 6,
        'HERMANA': 6,
        'TIO': 7,
        'TIA': 7,
        'PRIMO': 8,
        'PRIMA': 8,
        'OTRO': 9,
    }
    
    # Convertir a lista para ordenar en Python
    if hasattr(habitantes, 'order_by') and not isinstance(habitantes, list):
        habitantes = list(habitantes)
    
    # Ordenar: primero por grupo familiar (apellido + punto_referencia), luego por parentesco
    def obtener_orden(h):
        return (
            h.apellidos or '',
            h.punto_referencia or '',
            orden_parentesco.get(h.parentesco, 9),
            h.nombres or ''
        )
    
    habitantes = sorted(habitantes, key=obtener_orden)
    
    # Obtener fecha y hora actual
    ahora = datetime.now()
    fecha = ahora.strftime("%d/%m/%Y")
    hora = ahora.strftime("%I:%M %p")
    total = len(habitantes)
    
    # Determinar si mostramos la columna de parentesco
    mostrar_parentesco = bool(sector) or ver == 'todos'
    
    # Renderizar template HTML
    html_string = render_to_string('comunidad/reporte_pdf.html', {
        'habitantes': habitantes,
        'fecha': fecha,
        'hora': hora,
        'total': total,
        'busqueda': busqueda,
        'ver': ver,
        'etapa': etapa,
        'sector': sector,
        'mostrar_parentesco': mostrar_parentesco,
    })
    
    # Usar la función centralizada con marca de agua
    filename = 'censo_habitantes'
    if sector:
        sector_clean = sector.replace(' ', '_').replace('vía', 'via').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        filename += f'_{sector_clean}'
    
    return generar_pdf_con_marca(html_string, filename, mostrar_en_navegador=True)
# --- 4. MÓDULO DE ORGANIZACIÓN INFORMATIZACIONAL (ESTRUCTURA DE VOCERÍAS) ---
# ====================================================================================
@login_required(login_url='login')
def panel_organizacion(request):
    ids_ocupados = Voceria.objects.values_list('habitante_id', flat=True)
    todos_habitantes = Habitante.objects.all()
    
    habitantes_aptos = []
    for h in todos_habitantes:
        if h.cedula and h.cedula.strip() != '' and h.cedula.upper() != 'NO POSEE':
            if h.edad and h.edad >= 18:
                if h.id not in ids_ocupados:
                    habitantes_aptos.append(h)
                    
    habitantes_aptos.sort(key=lambda x: x.nombres)

    vocerias_db = Voceria.objects.select_related('habitante').all()
    mapa_vocerias = {f"{v.comite_codigo}_{v.tipo_vocero}": v for v in vocerias_db}
    
    iconos_comites = {
        'EJECUTIVO': 'bi bi-person-workspace', 'FINANZAS': 'bi bi-cash-coin',
        'CONTRALORIA': 'bi bi-eye-fill', 'VIVIENDA': 'bi bi-house-gear-fill',
        'SERVICIOS': 'bi bi-lightning-charge-fill', 'SALU': 'bi bi-hospital-fill',
        'PROT': 'bi bi-people-fill', 'ECON': 'bi bi-shop-window',
        'EDUC': 'bi bi-book-half', 'DEPO': 'bi bi-trophy-fill',
        'JUV': 'bi bi-backpack-fill', 'AMBI': 'bi bi-tree-fill',
        'COMU': 'bi bi-megaphone-fill'
    }

    comites_estructurados = []
    for codigo, nombre in Voceria.COMITES:
        v_princ = mapa_vocerias.get(f"{codigo}_VOCERO")
        v_sub = mapa_vocerias.get(f"{codigo}_SUBVOCERO")
        
        comites_estructurados.append({
            'codigo': codigo,
            'nombre': nombre,
            'icono': iconos_comites.get(codigo, 'bi bi-app-indicator'),
            'vocero': v_princ.habitante if v_princ else None,
            'id_voceria_princ': v_princ.id if v_princ else '',
            'subvocero': v_sub.habitante if v_sub else None,
            'id_voceria_sub': v_sub.id if v_sub else '',
        })

    from .models import JefeCalle
    jefes_db = JefeCalle.objects.select_related('habitante').all()
    mapa_jefes = {j.calle_nombre: j for j in jefes_db}

    calles_estructuradas = []
    for opcion_calle, _ in Habitante.CALLE_CHOICES:
        jefe_actual = mapa_jefes.get(opcion_calle)
        
        candidatos_calle = []
        for h in todos_habitantes:
            if h.calle_sector == opcion_calle:
                if h.cedula and h.cedula.strip() != '' and h.cedula.upper() != 'NO POSEE':
                    if h.edad and h.edad >= 18:
                        candidatos_calle.append(h)
        
        candidatos_calle.sort(key=lambda x: x.nombres)

        calles_estructuradas.append({
            'nombre_calle': opcion_calle,
            'jefe': jefe_actual.habitante if jefe_actual else None,
            'id_jefatura': jefe_actual.id if jefe_actual else '',
            'candidatos': candidatos_calle
        })

    contexto = {
        'todos_habitantes': habitantes_aptos,
        'comites': comites_estructurados,
        'calles': calles_estructuradas,
    }
    return render(request, 'comunidad/organizacion.html', contexto)


@login_required(login_url='login')
def asignar_jefe_calle(request):
    if request.method == 'POST':
        habitante_id = request.POST.get('habitante_id')
        calle_nombre = request.POST.get('calle_nombre')
        
        if not habitante_id:
            messages.error(request, "Debe seleccionar un ciudadano apto.")
            return redirect('organizacion')
            
        habitante = get_object_or_404(Habitante, id=habitante_id)
        
        from .models import JefeCalle
        JefeCalle.objects.update_or_create(
            calle_nombre=calle_nombre,
            defaults={'habitante': habitante}
        )
        messages.success(request, f"Asignación exitosa: {habitante.nombres} es el nuevo Jefe de la {calle_nombre}.")
    return redirect('organizacion')


@login_required(login_url='login')
def remover_jefe_calle(request):
    if request.method == 'POST':
        jefatura_id = request.POST.get('jefatura_id')
        if jefatura_id:
            from .models import JefeCalle
            jefatura = get_object_or_404(JefeCalle, id=jefatura_id)
            calle = jefatura.calle_nombre
            jefatura.delete()
            messages.success(request, f"Se ha revocado el cargo de Jefe de Calle para la {calle}.")
    return redirect('organizacion')

@login_required(login_url='login')
def asignar_vocero(request):
    if request.method == 'POST':
        habitante_id = request.POST.get('habitante_id')
        comite_codigo = request.POST.get('comite_codigo')
        tipo_vocero = request.POST.get('tipo_vocero')
        
        if not habitante_id:
            messages.error(request, "Debe seleccionar un habitante válido.")
            return redirect('organizacion')
            
        habitante = get_object_or_404(Habitante, id=habitante_id)
        
        ya_es_vocero = Voceria.objects.filter(comite_codigo=comite_codigo, habitante=habitante).first()
        if ya_es_vocero and ya_es_vocero.tipo_vocero != tipo_vocero:
            messages.error(request, f"El ciudadano {habitante.nombres} ya ocupa un rol activo en este comité.")
            return redirect('organizacion')
            
        Voceria.objects.update_or_create(
            comite_codigo=comite_codigo,
            tipo_vocero=tipo_vocero,
            defaults={'habitante': habitante}
        )
        messages.success(request, "Asignación registrada con éxito.")
    return redirect('organizacion')


@login_required(login_url='login')
def remover_vocero(request):
    if request.method == 'POST':
        voceria_id = request.POST.get('voceria_id')
        if voceria_id:
            voceria = get_object_or_404(Voceria, id=voceria_id)
            voceria.delete()
            messages.success(request, "Se ha retirado al vocero de sus funciones.")
    return redirect('organizacion')


# =====================================================================
#  MÓDULO DE EXPEDICIÓN DE CONSTANCIAS DE RESIDENCIA (PROCESAMIENTO PDF)
# =====================================================================
# Esta función es necesaria para que xhtml2pdf encuentre las imágenes

#NUMEROS A LETRAS
#NUMEROS A LETRAS
def numero_a_letras(n):
    if n == 0: return "cero"
    
    unidades = ["", "un", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", 
                "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte"]
    decenas = ["", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
    
    if n <= 20:
        return unidades[n]
    
    elif n < 30:
        return "veinti" + unidades[n % 10] if n > 20 else "veinte"
    
    elif n < 100:
        decena = decenas[n // 10]
        unidad = unidades[n % 10]
        if unidad == "":
            return decena
        else:
            return f"{decena} y {unidad}"
            
    elif n == 100:
        return "cien"
    
    return str(n)

def link_callback(uri, rel):
    result = finders.find(uri.replace(settings.STATIC_URL, ""))
    if result:
        return result
    return uri

@login_required(login_url='login')
@login_required(login_url='login')
def generar_constancia_pdf(request, habitante_id):
    habitante = get_object_or_404(Habitante, id=habitante_id)

    # =========================================================
    # CONTADOR PARA CONSTANCIA DE RESIDENCIA
    # =========================================================
    
    # 1. Obtener o crear el contador para tipo 'residencia'
    contador, created = ContadorConstancia.objects.get_or_create(
        tipo='residencia',
        defaults={'ultimo_numero': 0}
    )
    
    # 2. Incrementar el número
    nuevo_numero = contador.ultimo_numero + 1
    
    # 3. Guardar el nuevo número en la base de datos
    contador.ultimo_numero = nuevo_numero
    contador.save()
    
    # =========================================================
    # 0. FECHA FORMATEADA (DÍA, MES EN LETRAS, AÑO)
    # =========================================================
    from datetime import date
    
    # Lista de meses en español
    meses = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    
    hoy = date.today()
    dia = hoy.day
    mes = meses[hoy.month - 1]  # -1 porque la lista empieza en 0
    anio = hoy.year
    
    # =========================================================
    # 1. FUNCIÓN: OBTENER QUIEN FIRMA (VOCERO O SUPLENTE)
    # =========================================================
    def obtener_firmante(comite_codigo):
        """
        Retorna el habitante que debe firmar (vocero o subvocero).
        Prioridad: VOCERO > SUBVOCERO
        Retorna None si no hay ninguno.
        """
        # Buscar vocero principal
        vocero = Voceria.objects.filter(
            comite_codigo=comite_codigo, 
            tipo_vocero='VOCERO'
        ).select_related('habitante').first()
        
        if vocero:
            return vocero.habitante
        
        # Si no hay vocero, buscar subvocero
        subvocero = Voceria.objects.filter(
            comite_codigo=comite_codigo, 
            tipo_vocero='SUBVOCERO'
        ).select_related('habitante').first()
        
        if subvocero:
            return subvocero.habitante
        
        return None
    
    # =========================================================
    # 2. OBTENER LOS FIRMANTES DE CADA COMITÉ
    # =========================================================
    firmante_vivienda = obtener_firmante('VIVIENDA')
    firmante_servicios = obtener_firmante('SERVICIOS')
    firmante_salud = obtener_firmante('SALU')
    
    # =========================================================
    # 3. VERIFICAR FALTANTES (SOLO SI NO HAY NADIE)
    # =========================================================
    voceros_faltantes = []
    
    if not firmante_vivienda:
        voceros_faltantes.append("Vivienda y Hábitat")
    if not firmante_servicios:
        voceros_faltantes.append("Servicios Públicos")
    if not firmante_salud:
        voceros_faltantes.append("Salud Integral")

    # Si falta algún comité, mostrar el template de error
    if voceros_faltantes:
        return render(request, 'comunidad/error_voceros.html', {
            'faltantes': voceros_faltantes,
            'habitante_id': habitante_id
        })
    
    # =========================================================
    # 4. LÓGICA DE TIEMPO
    # =========================================================
    from dateutil.relativedelta import relativedelta
    
    hoy = date.today()
    delta = relativedelta(hoy, habitante.fecha_ingreso)
    años = delta.years
    meses_delta = delta.months
    dias_delta = delta.days

    if años == 0 and meses_delta == 0:
        tiempo_calculado = f"{numero_a_letras(dias_delta)} {'días' if dias_delta != 1 else 'día'}"
    elif años >= 10:
        tiempo_calculado = f"{numero_a_letras(años)} años"
    elif años > 0 and meses_delta > 0:
        tiempo_calculado = f"{numero_a_letras(años)} {'años' if años > 1 else 'año'} y {numero_a_letras(meses_delta)} {'meses' if meses_delta > 1 else 'mes'}"
    elif años > 0:
        tiempo_calculado = f"{numero_a_letras(años)} {'años' if años > 1 else 'año'}"
    else:
        tiempo_calculado = f"{numero_a_letras(meses_delta)} {'meses' if meses_delta > 1 else 'mes'}"

    # =========================================================
    # 5. DATOS DEL HABITANTE
    # =========================================================
    es_mayor = habitante.edad >= 18
    texto_edad = "mayor de edad" if es_mayor else "menor de edad"
    texto_nacionalidad = "venezolano(a)" if habitante.nacionalidad == 'V' else "extranjero(a)"
    tiene_cedula = bool(habitante.cedula and habitante.cedula.strip())
    
    # =========================================================
    # 6. CONTEXTO PARA EL TEMPLATE
    # =========================================================
    contexto = {
        # Fecha separada
        'dia': dia,
        'mes': mes,
        'anio': anio,
        
        # Datos del habitante
        'nombre': habitante.nombres,
        'apellido': habitante.apellidos,
        'texto_edad': texto_edad,
        'texto_nacionalidad': texto_nacionalidad,
        'tiene_cedula': tiene_cedula,
        'cedula': habitante.cedula_formateada,
        'ubicacion': habitante.get_calle_sector_display(),
        'tiempo': tiempo_calculado,
        'motivo': request.GET.get('motivo', 'No especificado'),
        'numero_constancia': nuevo_numero,
        
        # Datos de Vivienda
        'v_vivienda': f"{firmante_vivienda.nombres.title()} {firmante_vivienda.apellidos.title()}",
        'ci_vivienda': firmante_vivienda.cedula_formateada,
        'tel_vivienda': firmante_vivienda.telefono if firmante_vivienda and firmante_vivienda.telefono else "No posee",
        
        # Datos de Servicios
        'v_servicios': f"{firmante_servicios.nombres.title()} {firmante_servicios.apellidos.title()}",
        'ci_servicios': firmante_servicios.cedula_formateada,
        'tel_servicios': firmante_servicios.telefono if firmante_servicios and firmante_servicios.telefono else "No posee",
        
        # Datos de Salud
        'v_salud': f"{firmante_salud.nombres.title()} {firmante_salud.apellidos.title()}",
        'ci_salud': firmante_salud.cedula_formateada,
        'tel_salud': firmante_salud.telefono if firmante_salud and firmante_salud.telefono else "No posee",
        
        # Rutas de imágenes
        'escudoPath': settings.STATIC_URL + 'img/escudo_nacional.jpeg',
        'consejologoPath': settings.STATIC_URL + 'img/logo_comunas.jpeg',
        'marcaAguaPath': settings.STATIC_URL + 'img/marca_agua.jpg',
    }
    
    # =========================================================
    # 7. GENERAR PDF CON MARCA DE AGUA
    # =========================================================
    template = get_template('comunidad/constancia_residencia.html')
    html = template.render(contexto)
    
    # Usar la función centralizada con marca de agua
    filename = f"constancia_{habitante.cedula if tiene_cedula else habitante.id}"
    return generar_pdf_con_marca(html, filename, mostrar_en_navegador=True)

@login_required(login_url='login')
def censo_bombonas(request):
    from .models import JefeCalle
    
    calles_definidas = dict(Habitante.CALLE_CHOICES).keys()
    bloques_calles = []

    for nombre_calle in calles_definidas:
        jefe_calle_obj = JefeCalle.objects.select_related('habitante').filter(calle_nombre=nombre_calle).first()
        tiene_lider = f"{jefe_calle_obj.habitante.nombres} {jefe_calle_obj.habitante.apellidos}" if jefe_calle_obj else ""

        jefes = Habitante.objects.filter(calle_sector=nombre_calle, parentesco='JEFE').order_by('nombres')
        
        jefes_con_gas = []
        for j in jefes:
            registro_gas = getattr(j, 'censo_gas', None)
            jefes_con_gas.append({
                'jefe': j,
                'registro': registro_gas
            })
            
        bloques_calles.append({
            'nombre_calle': nombre_calle,
            'jefes_data': jefes_con_gas,
            'total_jefes': jefes.count(),
            'nombre_lider': tiene_lider
        })

    return render(request, 'comunidad/censo_bombonas.html', {
        'bloques_calles': bloques_calles
    })

@login_required(login_url='login')
def guardar_bombonas(request):
    if request.method == 'POST':
        jefe_id = request.POST.get('jefe_id')
        jefe = get_object_or_404(Habitante, id=jefe_id, parentesco='JEFE')
        
        registro, created = CensoBombona.objects.get_or_create(jefe_familia=jefe)
        
        registro.bombonas_10kg = int(request.POST.get('b10', 0))
        registro.bombonas_18kg = int(request.POST.get('b18', 0))
        registro.bombonas_27kg = int(request.POST.get('b27', 0))
        registro.bombonas_43kg = int(request.POST.get('b43', 0))
        registro.save()
        
        messages.success(request, f"Inventario de gas actualizado con éxito para {jefe.nombres} {jefe.apellidos}.")
        
    return redirect('censo_bombonas')

@login_required(login_url='login')
def exportar_bombonas_pdf(request):
    from .models import JefeCalle, CensoBombona
    
    nombre_calle = request.GET.get('calle', '').strip()
    
    jefe_calle_obj = JefeCalle.objects.select_related('habitante').filter(calle_nombre=nombre_calle).first()
    nombre_lider = f"{jefe_calle_obj.habitante.nombres} {jefe_calle_obj.habitante.apellidos}" if jefe_calle_obj else "NO ASIGNADO"
    
    jefes_queryset = Habitante.objects.filter(calle_sector=nombre_calle, parentesco='JEFE').order_by('nombres')
    
    registros_validos = []
    for j in jefes_queryset:
        p_10 = request.GET.get(f'p_10kg_{j.id}')
        p_18 = request.GET.get(f'p_18kg_{j.id}')
        p_27 = request.GET.get(f'p_27kg_{j.id}')
        p_43 = request.GET.get(f'p_43kg_{j.id}')
        
        cant_10 = int(p_10) if p_10 else 0
        cant_18 = int(p_18) if p_18 else 0
        cant_27 = int(p_27) if p_27 else 0
        cant_43 = int(p_43) if p_43 else 0
        
        if cant_10 > 0 or cant_18 > 0 or cant_27 > 0 or cant_43 > 0:
            registros_validos.append({
                'jefe': j,
                'registro': {
                    'bombonas_10kg': cant_10,
                    'bombonas_18kg': cant_18,
                    'bombonas_27kg': cant_27,
                    'bombonas_43kg': cant_43,
                }
            })
            
    ahora = datetime.now()
    fecha_formateada = ahora.strftime('%d/%m/%Y')
    hora_formateada = ahora.strftime('%I:%M %p')
    
    contexto = {
        'nombre_calle': nombre_calle,
        'nombre_lider': nombre_lider,
        'registros': registros_validos,
        'fecha': fecha_formateada,
        'hora': hora_formateada,
        'usuario': request.user.get_full_name() or request.user.username,
    }
    
    template = get_template('comunidad/reporte_bombonas.html')
    html_content = template.render(contexto)
    
    # ===== USAR LA FUNCIÓN CENTRALIZADA CON MARCA DE AGUA =====
    filename = f"Gas_{nombre_calle.replace(' ', '_')}"
    return generar_pdf_con_marca(html_content, filename, mostrar_en_navegador=False)

@login_required(login_url='login')
def censo_bombonas(request):
    from .models import JefeCalle
    
    calles_definidas = dict(Habitante.CALLE_CHOICES).keys()
    bloques_calles = []

    for nombre_calle in calles_definidas:
        jefe_calle_obj = JefeCalle.objects.select_related('habitante').filter(calle_nombre=nombre_calle).first()
        tiene_lider = f"{jefe_calle_obj.habitante.nombres} {jefe_calle_obj.habitante.apellidos}" if jefe_calle_obj else ""

        jefes = Habitante.objects.filter(calle_sector=nombre_calle, parentesco='JEFE').order_by('nombres')
        
        jefes_con_gas = []
        for j in jefes:
            registro_gas = getattr(j, 'censo_gas', None)
            jefes_con_gas.append({
                'jefe': j,
                'registro': registro_gas
            })
            
        bloques_calles.append({
            'nombre_calle': nombre_calle,
            'jefes_data': jefes_con_gas,
            'total_jefes': jefes.count(),
            'nombre_lider': tiene_lider
        })

    return render(request, 'comunidad/censo_bombonas.html', {
        'bloques_calles': bloques_calles
    })

@login_required(login_url='login')
def guardar_bombonas(request):
    if request.method == 'POST':
        jefe_id = request.POST.get('jefe_id')
        jefe = get_object_or_404(Habitante, id=jefe_id, parentesco='JEFE')
        
        registro, created = CensoBombona.objects.get_or_create(jefe_familia=jefe)
        
        registro.bombonas_10kg = int(request.POST.get('b10', 0))
        registro.bombonas_18kg = int(request.POST.get('b18', 0))
        registro.bombonas_27kg = int(request.POST.get('b27', 0))
        registro.bombonas_43kg = int(request.POST.get('b43', 0))
        registro.save()
        
        messages.success(request, f"Inventario de gas actualizado con éxito para {jefe.nombres} {jefe.apellidos}.")
        
    return redirect('censo_bombonas')

@login_required(login_url='login')
def exportar_censo_bombonas_pdf(request):
    from .models import JefeCalle, CensoBombona, Habitante
    
    nombre_calle = request.GET.get('calle', '').strip()
    
    # 1. Obtener al jefe de calle (si aplica para la etiqueta del PDF)
    jefe_calle_obj = JefeCalle.objects.select_related('habitante').filter(calle_nombre=nombre_calle).first() if nombre_calle else None
    nombre_lider = f"{jefe_calle_obj.habitante.nombres} {jefe_calle_obj.habitante.apellidos}" if jefe_calle_obj else "GENERAL / TODOS"
    
    # 2. Consultar TODAS las bombonas registradas
    query = CensoBombona.objects.all()
    if nombre_calle:
        query = query.filter(jefe_familia__calle_sector=nombre_calle)
        
    # Ordenamos por los nombres del jefe de familia asociado a ese censo
    registros = query.order_by('jefe_familia__nombres')
    
    # 3. Preparar el contexto
    ahora = datetime.now()
    contexto = {
        'nombre_calle': nombre_calle if nombre_calle else "TODO EL SECTOR",
        'nombre_lider': nombre_lider,
        'registros': registros,
        'fecha': ahora.strftime('%d/%m/%Y'),
        'hora': ahora.strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
    }
    
    # 4. Generación del PDF
    template = get_template('comunidad/reporte_censo_bombonas.html')
    html_content = template.render(contexto)
    
    # Usar la función centralizada con marca de agua
    nombre_archivo = f"Censo_Bombonas_{nombre_calle.replace(' ', '_') if nombre_calle else 'Total'}"
    return generar_pdf_con_marca(html_content, nombre_archivo, mostrar_en_navegador=False)# ====================================================================================
# --- 5. MÓDULO DE GESTIÓN Y AUDITORÍA DE PROYECTOS COMUNITARIOS ---
# ====================================================================================
# ====================================================================================
# --- 5. MÓDULO DE GESTIÓN Y AUDITORÍA DE PROYECTOS COMUNITARIOS ---
# ====================================================================================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal, InvalidOperation
from django.db.models import Sum
from .models import Proyecto, NotaSeguimiento, Voceria, MovimientoFinanciero

@login_required
def lista_proyectos(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        comite_codigo_form = request.POST.get('comite') 
        recursos_usd_raw = request.POST.get('recursos_usd', '0')
        descripcion = request.POST.get('descripcion', '').strip()
        ente_financista = request.POST.get('ente_financista', '').strip()
        
        if not nombre:
            messages.error(request, "Error: El nombre de la obra no puede estar vacío.")
            return redirect('lista_proyectos')
            
        # Validación de vocería
        comites_con_vocero = list(Voceria.objects.exclude(habitante__isnull=True).values_list('comite_codigo', flat=True).distinct())
        comites_con_vocero_str = [str(c).strip() for c in comites_con_vocero]
        
        if str(comite_codigo_form).strip() not in comites_con_vocero_str:
            messages.error(request, "Error: El comité seleccionado no dispone de un vocero registrado.")
            return redirect('lista_proyectos')
        
        try:
            recursos_usd = Decimal(recursos_usd_raw)
            if recursos_usd < 0: raise InvalidOperation
        except (ValueError, InvalidOperation):
            messages.error(request, "Error: El monto en USD debe ser un número válido.")
            return redirect('lista_proyectos')
            
        # --- CREACIÓN DEL PROYECTO ---
        nuevo_proyecto = Proyecto.objects.create(
            nombre=nombre,
            comite=comite_codigo_form,
            recursos_usd=recursos_usd,
            descripcion=descripcion,
            ente_financista=ente_financista if ente_financista else "Fondo Comunal Km 5",
            estado='APROBADO',
            es_compromiso=True # Marcamos el compromiso al crear
        )
        
        NotaSeguimiento.objects.create(
            proyecto=nuevo_proyecto,
            observacion=f"Proyecto registrado. Fondos bloqueados por ${recursos_usd} USD.",
            usuario_registro=request.user.username
        )
        
        messages.success(request, "¡Proyecto registrado! Fondos bloqueados correctamente.")
        return redirect('lista_proyectos')

    # --- LÓGICA GET (Cálculo de Disponibilidad Real) ---
    # 1. Calculamos saldo bruto
    ingresos = MovimientoFinanciero.objects.filter(tipo='INGRESO', moneda='USD').aggregate(total=Sum('monto'))['total'] or 0
    egresos = MovimientoFinanciero.objects.filter(tipo='EGRESO', moneda='USD').aggregate(total=Sum('monto'))['total'] or 0
    saldo_bruto = ingresos - egresos
    
    # 2. Calculamos los fondos que están actualmente comprometidos en proyectos APROBADOS
    total_comprometido = Proyecto.objects.filter(es_compromiso=True, estado='APROBADO').aggregate(total=Sum('recursos_usd'))['total'] or 0
    
    # 3. Disponibilidad real para el usuario
    usd_disponible_real = saldo_bruto - total_comprometido

    comites_validos_raw = Voceria.objects.exclude(habitante__isnull=True).values_list('comite_codigo', flat=True).distinct()
    comites_validos_str = [str(codigo).strip() for codigo in comites_validos_raw]
    comites_opciones = [(codigo, nombre_comite) for codigo, nombre_comite in Voceria.COMITES if str(codigo).strip() in comites_validos_str]

    contexto = {
        'aprobados': Proyecto.objects.filter(estado='APROBADO').order_by('-id'),
        'ejecucion': Proyecto.objects.filter(estado='EN_EJECUCION').order_by('-id'),
        'culminados': Proyecto.objects.filter(estado='CULMINADO').order_by('-id'),
        'comites_opciones': comites_opciones or Voceria.COMITES,
        'usd_disponible': usd_disponible_real, # Usamos el valor neto
    }
    return render(request, 'comunidad/proyectos.html', contexto)

@login_required
def avanzar_proyecto(request, id):
    proyecto = get_object_or_404(Proyecto, id=id)
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        
        # Lógica de liberación: Si pasa de Aprobado a En Ejecución, liberamos el compromiso
        if proyecto.estado == 'APROBADO' and nuevo_estado == 'EN_EJECUCION':
            proyecto.es_compromiso = False
            
        proyecto.estado = nuevo_estado
        proyecto.save()
        messages.success(request, f"Estado del proyecto '{proyecto.nombre}' actualizado.")
        
    return redirect('lista_proyectos')

@login_required(login_url='login')
def exportar_proyecto_pdf(request, proyecto_id):
    # Buscamos el proyecto o disparamos error 404 si no existe
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    
    # Extraemos las notas de seguimiento de contraloría social asociadas
    notas = NotaSeguimiento.objects.filter(proyecto=proyecto).order_by('-fecha_registro')
    
    # Obtenemos el nombre legible del comité desde la tupla Voceria.COMITES
    comite_nombre = dict(Voceria.COMITES).get(str(proyecto.comite)) or dict(Voceria.COMITES).get(int(proyecto.comite) if proyecto.comite.isdigit() else proyecto.comite) or proyecto.comite
    
    contexto = {
        'proyecto': proyecto,
        'comite_nombre': comite_nombre,
        'notas': notas,
        'usuario': request.user.username,
        'fecha_reporte': timezone.now()
    }
    
    # Renderizamos la plantilla HTML
    template = get_template('comunidad/pdf_proyecto.html')
    html = template.render(contexto)
    
    # Usar la función centralizada con marca de agua
    filename = f"Expediente_Proyecto_{proyecto.id}"
    return generar_pdf_con_marca(html, filename, mostrar_en_navegador=False)

@login_required(login_url='login')
def avanzar_fase_proyecto(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    
    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        
        # TRANSICIÓN: DE APROBADO A EN EJECUCION (Aquí se descuenta el dinero)
        if proyecto.estado == 'APROBADO' and nuevo_estado == 'EN_EJECUCION':
            
            # 1. Registramos el Egreso real en Finanzas (el eslabón que faltaba)
            MovimientoFinanciero.objects.create(
                tipo='EGRESO',
                concepto=f"Ejecución de obra: {proyecto.nombre}",
                monto=proyecto.recursos_usd,
                moneda='USD',
                usuario_registrador=request.user.username
            )
            
            # 2. Actualizamos el proyecto
            proyecto.ejecutor = request.POST.get('ejecutor')
            proyecto.fecha_inicio_real = timezone.now().date()
            proyecto.estado = 'EN_EJECUCION'
            
            # 3. ELIMINA ESTA LÍNEA - NO PONGAS recursos_usd = 0
            # proyecto.recursos_usd = 0  # <--- ¡BORRA ESTA LÍNEA!
            proyecto.save()
            
            NotaSeguimiento.objects.create(
                proyecto=proyecto,
                observacion=f"Hito de inicio: Se asignan recursos a: {proyecto.ejecutor}. Fondos ejecutados.",
                usuario_registro=request.user.username
            )
            messages.success(request, "La obra ha iniciado. Los fondos han sido descontados del saldo disponible.")
            
        # TRANSICIÓN: DE EN EJECUCIÓN A CULMINADO
        elif proyecto.estado == 'EN_EJECUCION' and nuevo_estado == 'CULMINADO':
            proyecto.fecha_cierre_real = timezone.now().date()
            proyecto.estado = 'CULMINADO'
            proyecto.save()
            
            NotaSeguimiento.objects.create(
                proyecto=proyecto,
                observacion="Hito de Cierre: Proyecto auditado y culminado. Se aplica candado digital.",
                usuario_registro=request.user.username
            )
            messages.warning(request, "¡Proyecto Culminado! El expediente ha sido archivado.")
            
        else:
            messages.error(request, "Acción inválida. El flujo de fases es estrictamente lineal.")
            
    return redirect('lista_proyectos')

@login_required(login_url='login')
def agregar_nota_proyecto(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    
    if proyecto.estado == 'CULMINADO':
        messages.error(request, "No se pueden insertar folios en la bitácora de un proyecto ya cerrado y culminado.")
        return redirect('lista_proyectos')
        
    if request.method == 'POST':
        observacion = request.POST.get('observacion')
        if observacion:
            NotaSeguimiento.objects.create(
                proyecto=proyecto,
                observacion=observacion,
                usuario_registro=request.user.username
            )
            messages.success(request, "Asiento cargado correctamente en el libro digital de contraloría.")
            
    return redirect('lista_proyectos')

#PDF PROYECTOS
@login_required(login_url='login')
def exportar_proyecto_pdf(request, proyecto_id):
    # Buscamos el proyecto o disparamos error 404 si no existe
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    
    # Extraemos las notas de seguimiento de contraloría social asociadas
    notas = NotaSeguimiento.objects.filter(proyecto=proyecto).order_by('-fecha_registro')
    
    # Obtenemos el nombre legible del comité desde la tupla Voceria.COMITES
    comite_nombre = dict(Voceria.COMITES).get(str(proyecto.comite)) or dict(Voceria.COMITES).get(int(proyecto.comite) if proyecto.comite.isdigit() else proyecto.comite) or proyecto.comite
    
    contexto = {
        'proyecto': proyecto,
        'comite_nombre': comite_nombre,
        'notas': notas,
        'usuario': request.user.username,
        'fecha_reporte': timezone.now()
    }
    
    # Renderizamos la plantilla HTML
    template = get_template('comunidad/pdf_proyecto.html')
    html = template.render(contexto)
    
    # Usar la función centralizada con marca de agua
    filename = f"Expediente_Proyecto_{proyecto.id}"
    return generar_pdf_con_marca(html, filename, mostrar_en_navegador=False)

#finanzas
# --- 1. ACTUALIZACIÓN DEL PANEL DE FINANZAS ---
@login_required(login_url='login')
def panel_finanzas(request, moneda='USD'):
    tiene_finanzas = Voceria.objects.filter(comite_codigo__icontains='finan').exists()
    tiene_contraloria = Voceria.objects.filter(comite_codigo__icontains='contra').exists()
    permite_registro = tiene_finanzas and tiene_contraloria
    
    movimientos = MovimientoFinanciero.objects.filter(moneda=moneda.upper()).order_by('-fecha_registro')
    
    total_ingresos = movimientos.filter(tipo='INGRESO').aggregate(s=Sum('monto'))['s'] or 0
    total_egresos = movimientos.filter(tipo='EGRESO').aggregate(s=Sum('monto'))['s'] or 0
    
    fondos_comprometidos = 0
    if moneda.upper() == 'USD':
        fondos_comprometidos = Proyecto.objects.filter(
            estado__in=['APROBADO', 'EN_EJECUCION']
        ).aggregate(total=Sum('recursos_usd'))['total'] or 0
    
    saldo_real_disponible = (total_ingresos - total_egresos) - fondos_comprometidos
    
    contexto = {
        'movimientos': movimientos,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'fondos_comprometidos': fondos_comprometidos,
        'saldo_real_disponible': saldo_real_disponible,
        'permite_registro': permite_registro,
        'moneda_activa': moneda.upper(),
    }
    return render(request, 'comunidad/finanzas.html', contexto)

# --- 2. ACTUALIZACIÓN DEL GUARDADO DE MOVIMIENTOS ---
@login_required(login_url='login')
def guardar_movimiento(request, moneda='USD'):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        concepto = request.POST.get('concepto')
        monto_str = request.POST.get('monto')

        if tipo and concepto and monto_str:
            try:
                monto = Decimal(monto_str)
            except ValueError:
                messages.error(request, "El monto ingresado no es válido.")
                return redirect('panel_finanzas_moneda', moneda=moneda)

            if tipo == 'EGRESO' and moneda.upper() == 'USD':
                movimientos = MovimientoFinanciero.objects.filter(moneda='USD')
                total_ingresos = movimientos.filter(tipo='INGRESO').aggregate(s=Sum('monto'))['s'] or 0
                total_egresos = movimientos.filter(tipo='EGRESO').aggregate(s=Sum('monto'))['s'] or 0
                fondos_comprometidos = Proyecto.objects.filter(estado__in=['APROBADO', 'EN_EJECUCION']).aggregate(total=Sum('recursos_usd'))['total'] or 0
                saldo_real_disponible = (total_ingresos - total_egresos) - fondos_comprometidos
                
                if monto > saldo_real_disponible:
                    messages.error(request, f"Operación rechazada: Solo dispone de ${saldo_real_disponible:.2f} USD libres.")
                    return redirect('panel_finanzas_moneda', moneda=moneda)

            MovimientoFinanciero.objects.create(
                tipo=tipo,
                concepto=concepto,
                monto=monto,
                moneda=moneda.upper(),
                usuario_registrador=request.user.username
            )
            messages.success(request, f"Movimiento registrado en {moneda.upper()}.")
            
    return redirect('panel_finanzas_moneda', moneda=moneda)

# --- 2. ACTUALIZACIÓN DEL GUARDADO DE MOVIMIENTOS ---
@login_required(login_url='login')
def guardar_movimiento(request, moneda='USD'):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        concepto = request.POST.get('concepto')
        monto_str = request.POST.get('monto')

        if tipo and concepto and monto_str:
            try:
                monto = Decimal(monto_str)
            except ValueError:
                messages.error(request, "El monto ingresado no es válido.")
                return redirect('panel_finanzas_moneda', moneda=moneda)

            if tipo == 'EGRESO' and moneda.upper() == 'USD':
                movimientos = MovimientoFinanciero.objects.filter(moneda='USD')
                total_ingresos = movimientos.filter(tipo='INGRESO').aggregate(s=Sum('monto'))['s'] or 0
                total_egresos = movimientos.filter(tipo='EGRESO').aggregate(s=Sum('monto'))['s'] or 0
                fondos_comprometidos = Proyecto.objects.filter(estado__in=['APROBADO', 'EN_EJECUCION']).aggregate(total=Sum('recursos_usd'))['total'] or 0
                saldo_real_disponible = (total_ingresos - total_egresos) - fondos_comprometidos
                
                if monto > saldo_real_disponible:
                    messages.error(request, f"Operación rechazada: Solo dispone de ${saldo_real_disponible:.2f} USD libres.")
                    return redirect('panel_finanzas_moneda', moneda=moneda)

            MovimientoFinanciero.objects.create(
                tipo=tipo,
                concepto=concepto,
                monto=monto,
                moneda=moneda.upper(),
                usuario_registrador=request.user.username
            )
            messages.success(request, f"Movimiento registrado en {moneda.upper()}.")
            
    return redirect('panel_finanzas_moneda', moneda=moneda)

from django.db.models import Sum

from django.db.models import Sum

@login_required(login_url='login')
def exportar_finanzas_pdf(request, moneda='USD'):
    from django.db.models import Sum
    
    moneda_upper = moneda.upper()
    
    # 1. Filtramos los movimientos exactamente igual que en panel_finanzas
    movimientos = MovimientoFinanciero.objects.filter(moneda=moneda_upper).order_by('-fecha_registro')
    
    # 2. Calculamos los totales igual que en panel_finanzas
    total_ingresos = movimientos.filter(tipo='INGRESO').aggregate(s=Sum('monto'))['s'] or 0
    total_egresos = movimientos.filter(tipo='EGRESO').aggregate(s=Sum('monto'))['s'] or 0
    
    # 3. REPLICAMOS LA LÓGICA DE FONDOS COMPROMETIDOS
    fondos_comprometidos = 0
    if moneda_upper == 'USD':
        fondos_comprometidos = Proyecto.objects.filter(
            estado__in=['APROBADO', 'EN_EJECUCION']
        ).aggregate(total=Sum('recursos_usd'))['total'] or 0
    
    # 4. Cálculo del saldo disponible (idéntico al panel)
    saldo_real_disponible = (total_ingresos - total_egresos) - fondos_comprometidos
    
    # 5. Obtención de voceros (igual que en el panel)
    voceros_finanzas = Voceria.objects.filter(comite_codigo='FINANZAS')
    voceros_contraloria = Voceria.objects.filter(comite_codigo='CONTRALORIA')
    
    contexto = {
        'movimientos': movimientos,
        'total_ingresos': total_ingresos,
        'total_egresos': total_egresos,
        'fondos_comprometidos': fondos_comprometidos,
        'saldo_real_disponible': saldo_real_disponible,
        'usuario': request.user.username,
        'fecha_reporte': timezone.now(),
        'moneda': moneda_upper,
        'voceros_finanzas': voceros_finanzas,
        'voceros_contraloria': voceros_contraloria,
    }
    
    template = get_template('comunidad/pdf_finanzas.html')
    html = template.render(contexto)
    
    # Usar la función centralizada con marca de agua
    filename = f"reporte_finanzas_{moneda_upper}"
    return generar_pdf_con_marca(html, filename, mostrar_en_navegador=False)
#CLAP
from django.shortcuts import render
# Asegúrate de importar los modelos necesarios desde tu archivo models.py
from .models import Habitante, JefeCalle
def gestion_clap(request):
    # Obtenemos todas las calles definidas en las opciones del modelo

    calles_disponibles = dict(Habitante.CALLE_CHOICES).keys()
    bloques_calles = []

    for nombre_calle in calles_disponibles:
        # Buscamos quién es el Jefe de Calle registrado para esta calle
        jefe_calle_registro = JefeCalle.objects.filter(calle_nombre=nombre_calle).first()
        
        # Obtenemos los Jefes de Familia de esta calle
        jefes_familia = Habitante.objects.filter(
            calle_sector=nombre_calle, 
            parentesco='JEFE'
        )
        
        bloques_calles.append({
            'nombre_calle': nombre_calle,
            'jefe_calle': jefe_calle_registro.habitante if jefe_calle_registro else None,
            'jefes_data': jefes_familia,
            'total_jefes': jefes_familia.count()
        })

    contexto = {
        'titulo': 'Gestión CLAP - SIA KM5',
        'bloques_calles': bloques_calles,
    }
    
    return render(request, 'comunidad/gestion_clap.html', contexto)

@login_required(login_url='login')
def exportar_clap_pdf(request):
    from .models import JefeCalle, Habitante

    nombre_calle = request.GET.get('calle', '').strip()
    ids_marcados = request.GET.getlist('beneficiario_id')
    
    jefe_calle_obj = JefeCalle.objects.select_related('habitante').filter(calle_nombre=nombre_calle).first()
    nombre_lider = f"{jefe_calle_obj.habitante.nombres} {jefe_calle_obj.habitante.apellidos}" if jefe_calle_obj else "NO ASIGNADO"
    
    registros = Habitante.objects.filter(id__in=ids_marcados).order_by('nombres')
    
    contexto = {
        'nombre_calle': nombre_calle,
        'nombre_lider': nombre_lider,
        'registros': registros,
        'fecha': datetime.now().strftime('%d/%m/%Y'),
        'hora': datetime.now().strftime('%I:%M %p'),
        'usuario': request.user.get_full_name() or request.user.username,
    }
    
    template = get_template('comunidad/reporte_censo_clap.html')
    html_content = template.render(contexto)
    
    # Usar la función centralizada con marca de agua
    filename = f"Entrega_CLAP_{nombre_calle.replace(' ', '_')}"
    return generar_pdf_con_marca(html_content, filename, mostrar_en_navegador=False)
#CARTA AVAL COMERCIAL
# ====================================================================================
# CARTA AVAL COMERCIAL - CON VALIDACIÓN DE EDAD Y CÉDULA
# ====================================================================================
# ====================================================================================
# CARTA AVAL COMERCIAL - VERSIÓN ORIGINAL (SIN VALIDACIÓN ADICIONAL)
# ====================================================================================
@login_required
def generar_carta_aval(request, habitante_id):
    """Genera la Carta Aval de Funcionamiento Comercial"""
    from datetime import date
    
    habitante = get_object_or_404(Habitante, pk=habitante_id)
    
    # =========================================================
    # CONTADOR PARA CARTA AVAL COMERCIAL
    # =========================================================
    contador, created = ContadorConstancia.objects.get_or_create(
        tipo='comercial',
        defaults={'ultimo_numero': 0}
    )
    nuevo_numero = contador.ultimo_numero + 1
    contador.ultimo_numero = nuevo_numero
    contador.save()
    
    # =========================================================
    # DATOS DEL HABITANTE
    # =========================================================
    nombre = habitante.nombres.title()
    apellido = habitante.apellidos.title()
    cedula = habitante.cedula_formateada
    
    # =========================================================
    # OBTENER VOCEROS FIRMANTES
    # =========================================================
    def obtener_firmante(comite_codigo):
        vocero = Voceria.objects.filter(comite_codigo=comite_codigo, tipo_vocero='VOCERO').first()
        if vocero:
            return vocero.habitante
        subvocero = Voceria.objects.filter(comite_codigo=comite_codigo, tipo_vocero='SUBVOCERO').first()
        if subvocero:
            return subvocero.habitante
        return None
    
    firmante_economia = obtener_firmante('ECON')
    firmante_vivienda = obtener_firmante('VIVIENDA')
    firmante_servicios = obtener_firmante('SERVICIOS')
    
    # =========================================================
    # FECHA FORMATEADA
    # =========================================================
    hoy = date.today()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    dia = hoy.day
    mes = meses[hoy.month - 1]
    anio = hoy.year
    
    # =========================================================
    # CONTEXTO PARA EL TEMPLATE
    # =========================================================
    contexto = {
        'numero_constancia': nuevo_numero,
        'nombre': nombre,
        'apellido': apellido,
        'cedula': cedula,
        'dia': dia,
        'mes': mes,
        'anio': anio,
        'nombre_comercio': request.GET.get('nombre_comercio', '_________________________'),
        'rif': request.GET.get('rif', '_________________________'),
        'tipo_solicitud': request.GET.get('tipo_solicitud', '_________________________'),
        'numero_patente': request.GET.get('numero_patente', '_________________________'),
        'rubro': request.GET.get('rubro', '_________________________'),
        'firma': request.GET.get('firma', '_________________________'),
        'v_economia': f"{firmante_economia.nombres.title()} {firmante_economia.apellidos.title()}" if firmante_economia else "_________________________",
        'ci_economia': firmante_economia.cedula_formateada if firmante_economia else "_________________________",
        'tel_economia': firmante_economia.telefono if firmante_economia and firmante_economia.telefono else "No posee",
        'v_vivienda': f"{firmante_vivienda.nombres.title()} {firmante_vivienda.apellidos.title()}" if firmante_vivienda else "_________________________",
        'ci_vivienda': firmante_vivienda.cedula_formateada if firmante_vivienda else "__________",
        'tel_vivienda': firmante_vivienda.telefono if firmante_vivienda and firmante_vivienda.telefono else "No posee",
        'v_servicios': f"{firmante_servicios.nombres.title()} {firmante_servicios.apellidos.title()}" if firmante_servicios else "_________________________",
        'ci_servicios': firmante_servicios.cedula_formateada if firmante_servicios else "_________________________",
        'tel_servicios': firmante_servicios.telefono if firmante_servicios and firmante_servicios.telefono else "No posee",
        'escudoPath': settings.STATIC_URL + 'img/escudo_nacional.jpeg',
        'consejologoPath': settings.STATIC_URL + 'img/logo_comunas.jpeg',
    }
    
    # =========================================================
    # GENERAR PDF CON MARCA DE AGUA
    # =========================================================
    template = get_template('comunidad/carta_aval_comercial.html')
    html = template.render(contexto)
    
    filename = f"carta_aval_{habitante.cedula if habitante.cedula else habitante.id}"
    return generar_pdf_con_marca(html, filename, mostrar_en_navegador=True)# ====================================================================================
# --- CONSTANCIA DE FALLECIMIENTO CON GUARDADO EN BD ---
# ====================================================================================
@login_required(login_url='login')
def generar_constancia_fallecimiento_pdf(request, habitante_id):
    """
    Genera Constancia de Fallecimiento para un habitante
    - Si está vivo: pide hora y causa, guarda en BD, marca como fallecido SOLO si el PDF se genera
    - Si ya falleció: usa los datos guardados y genera PDF directamente
    """
    from datetime import date, datetime
    
    habitante = get_object_or_404(Habitante, id=habitante_id)
    
    # =========================================================
    # CASO 1: EL HABITANTE YA ESTÁ FALLECIDO (tiene datos guardados)
    # =========================================================
    if not habitante.vivo:
        # Usar los datos ya almacenados en la base de datos
        fecha_fallecimiento = habitante.fecha_fallecimiento
        anio_fallecimiento = fecha_fallecimiento.year
        mes_fallecimiento = fecha_fallecimiento.month
        dia_fallecimiento = fecha_fallecimiento.day
        hora_fallecimiento = habitante.hora_fallecimiento
        causa_fallecimiento = habitante.causa_fallecimiento
        
        # Calcular edad al momento del fallecimiento
        edad_fallecimiento = fecha_fallecimiento.year - habitante.fecha_nacimiento.year
        if (fecha_fallecimiento.month, fecha_fallecimiento.day) < (habitante.fecha_nacimiento.month, habitante.fecha_nacimiento.day):
            edad_fallecimiento -= 1
        if edad_fallecimiento < 0:
            edad_fallecimiento = 0
        
        # Calcular tiempo de residencia en letras
        fecha_ingreso = habitante.fecha_ingreso
        tiempo_residencia_numero = fecha_fallecimiento.year - fecha_ingreso.year
        if (fecha_fallecimiento.month, fecha_fallecimiento.day) < (fecha_ingreso.month, fecha_ingreso.day):
            tiempo_residencia_numero -= 1
        if tiempo_residencia_numero < 0:
            tiempo_residencia_numero = 0
        tiempo_residencia_letras = numero_a_letras_residencia(tiempo_residencia_numero)
        
        # Resto de datos
        nombre = habitante.nombres.title()
        apellido = habitante.apellidos.title()
        tiene_cedula = bool(habitante.cedula and habitante.cedula.strip())
        cedula_texto = habitante.cedula_formateada if tiene_cedula else "NO POSEE"
        ubicacion = habitante.get_calle_sector_display()
        
        # Obtener voceros
        firmante_vivienda, firmante_servicios, firmante_salud, voceros_faltantes = obtener_voceros_firmantes()
        
        if voceros_faltantes:
            return render(request, 'comunidad/error_voceros.html', {
                'faltantes': voceros_faltantes,
                'habitante_id': habitante_id,
                'tipo': 'fallecimiento'
            })
        
        # Fechas formateadas
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        mes_fallecimiento_texto = meses[mes_fallecimiento - 1]
        hoy = date.today()
        dia_expedicion = hoy.day
        mes_expedicion = meses[hoy.month - 1]
        anio_expedicion = hoy.year
        
        contexto = {
            'nombre': nombre,
            'apellido': apellido,
            'edad': edad_fallecimiento,
            'tiene_cedula': tiene_cedula,
            'cedula': cedula_texto,
            'ubicacion': ubicacion,
            'tiempo_residencia': tiempo_residencia_letras,
            'dia_fallecimiento': dia_fallecimiento,
            'mes_fallecimiento': mes_fallecimiento_texto,
            'anio_fallecimiento': anio_fallecimiento,
            'hora_fallecimiento': hora_fallecimiento,
            'causa_fallecimiento': causa_fallecimiento,
            'dia_expedicion': dia_expedicion,
            'mes_expedicion': mes_expedicion,
            'anio_expedicion': anio_expedicion,
            'v_vivienda': f"{firmante_vivienda.nombres.title()} {firmante_vivienda.apellidos.title()}",
            'ci_vivienda': firmante_vivienda.cedula_formateada,
            'tel_vivienda': firmante_vivienda.telefono if firmante_vivienda.telefono else "No posee",
            'v_servicios': f"{firmante_servicios.nombres.title()} {firmante_servicios.apellidos.title()}",
            'ci_servicios': firmante_servicios.cedula_formateada,
            'tel_servicios': firmante_servicios.telefono if firmante_servicios.telefono else "No posee",
            'v_salud': f"{firmante_salud.nombres.title()} {firmante_salud.apellidos.title()}",
            'ci_salud': firmante_salud.cedula_formateada,
            'tel_salud': firmante_salud.telefono if firmante_salud.telefono else "No posee",
            'escudoPath': settings.STATIC_URL + 'img/escudo_nacional.jpeg',
            'consejologoPath': settings.STATIC_URL + 'img/logo_comunas.jpeg',
        }
        
        template = get_template('comunidad/constancia_fallecimiento.html')
        html = template.render(contexto)
        
        filename = f"constancia_fallecimiento_{habitante.id}_{fecha_fallecimiento}"
        return generar_pdf_con_marca(html, filename, mostrar_en_navegador=True)
    
    # =========================================================
    # CASO 2: PRIMERA VEZ - HABITANTE VIVO (pedir datos y guardar)
    # =========================================================
    
    fecha_fallecimiento = date.today()
    anio_fallecimiento = fecha_fallecimiento.year
    mes_fallecimiento = fecha_fallecimiento.month
    dia_fallecimiento = fecha_fallecimiento.day
    
    # Obtener hora y causa del request
    hora_seleccionada = request.GET.get('hora_fallecimiento', '')
    causa_fallecimiento = request.GET.get('causa_fallecimiento', '')
    
    # Validar que llegaron los datos
    if not hora_seleccionada or not causa_fallecimiento:
        messages.error(request, "Debe especificar la hora y la causa del fallecimiento.")
        return redirect('lista_habitantes')
    
    # Diccionario para convertir hora a texto natural
    horas_texto = {
        '1': '1 de la madrugada', '2': '2 de la madrugada', '3': '3 de la madrugada',
        '4': '4 de la madrugada', '5': '5 de la madrugada', '6': '6 de la mañana',
        '7': '7 de la mañana', '8': '8 de la mañana', '9': '9 de la mañana',
        '10': '10 de la mañana', '11': '11 de la mañana', '12': '12 del mediodía',
        '13': '1 de la tarde', '14': '2 de la tarde', '15': '3 de la tarde',
        '16': '4 de la tarde', '17': '5 de la tarde', '18': '6 de la tarde',
        '19': '7 de la noche', '20': '8 de la noche', '21': '9 de la noche',
        '22': '10 de la noche', '23': '11 de la noche', '24': '12 de la noche',
    }
    
    hora_fallecimiento = horas_texto.get(str(hora_seleccionada), '_________')
    
    # =========================================================
    # VERIFICAR VOCEROS ANTES DE GUARDAR CUALQUIER COSA
    # =========================================================
    firmante_vivienda, firmante_servicios, firmante_salud, voceros_faltantes = obtener_voceros_firmantes()
    
    if voceros_faltantes:
        return render(request, 'comunidad/error_voceros.html', {
            'faltantes': voceros_faltantes,
            'habitante_id': habitante_id,
            'tipo': 'fallecimiento'
        })
    
    # =========================================================
    # GENERAR EL PDF PRIMERO (antes de guardar en BD)
    # =========================================================
    nombre = habitante.nombres.title()
    apellido = habitante.apellidos.title()
    
    edad_fallecimiento = fecha_fallecimiento.year - habitante.fecha_nacimiento.year
    if (fecha_fallecimiento.month, fecha_fallecimiento.day) < (habitante.fecha_nacimiento.month, habitante.fecha_nacimiento.day):
        edad_fallecimiento -= 1
    if edad_fallecimiento < 0:
        edad_fallecimiento = 0
    
    tiene_cedula = bool(habitante.cedula and habitante.cedula.strip())
    cedula_texto = habitante.cedula_formateada if tiene_cedula else "NO POSEE"
    ubicacion = habitante.get_calle_sector_display()
    
    # Tiempo de residencia en letras
    fecha_ingreso = habitante.fecha_ingreso
    tiempo_residencia_numero = fecha_fallecimiento.year - fecha_ingreso.year
    if (fecha_fallecimiento.month, fecha_fallecimiento.day) < (fecha_ingreso.month, fecha_ingreso.day):
        tiempo_residencia_numero -= 1
    if tiempo_residencia_numero < 0:
        tiempo_residencia_numero = 0
    tiempo_residencia_letras = numero_a_letras_residencia(tiempo_residencia_numero)
    
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    mes_fallecimiento_texto = meses[mes_fallecimiento - 1]
    
    hoy = date.today()
    dia_expedicion = hoy.day
    mes_expedicion = meses[hoy.month - 1]
    anio_expedicion = hoy.year
    
    contexto = {
        'nombre': nombre,
        'apellido': apellido,
        'edad': edad_fallecimiento,
        'tiene_cedula': tiene_cedula,
        'cedula': cedula_texto,
        'ubicacion': ubicacion,
        'tiempo_residencia': tiempo_residencia_letras,
        'dia_fallecimiento': dia_fallecimiento,
        'mes_fallecimiento': mes_fallecimiento_texto,
        'anio_fallecimiento': anio_fallecimiento,
        'hora_fallecimiento': hora_fallecimiento,
        'causa_fallecimiento': causa_fallecimiento,
        'dia_expedicion': dia_expedicion,
        'mes_expedicion': mes_expedicion,
        'anio_expedicion': anio_expedicion,
        'v_vivienda': f"{firmante_vivienda.nombres.title()} {firmante_vivienda.apellidos.title()}",
        'ci_vivienda': firmante_vivienda.cedula_formateada,
        'tel_vivienda': firmante_vivienda.telefono if firmante_vivienda.telefono else "No posee",
        'v_servicios': f"{firmante_servicios.nombres.title()} {firmante_servicios.apellidos.title()}",
        'ci_servicios': firmante_servicios.cedula_formateada,
        'tel_servicios': firmante_servicios.telefono if firmante_servicios.telefono else "No posee",
        'v_salud': f"{firmante_salud.nombres.title()} {firmante_salud.apellidos.title()}",
        'ci_salud': firmante_salud.cedula_formateada,
        'tel_salud': firmante_salud.telefono if firmante_salud.telefono else "No posee",
        'escudoPath': settings.STATIC_URL + 'img/escudo_nacional.jpeg',
        'consejologoPath': settings.STATIC_URL + 'img/logo_comunas.jpeg',
    }
    
    template = get_template('comunidad/constancia_fallecimiento.html')
    html = template.render(contexto)
    
    # Generar el PDF con la función centralizada
    filename = f"constancia_fallecimiento_{habitante.id}_{fecha_fallecimiento}"
    response = generar_pdf_con_marca(html, filename, mostrar_en_navegador=True)
    
    # Si el PDF se generó correctamente, guardar en BD
    if response.status_code == 200:
        habitante.vivo = False
        habitante.fecha_fallecimiento = fecha_fallecimiento
        habitante.hora_fallecimiento = hora_fallecimiento
        habitante.causa_fallecimiento = causa_fallecimiento
        habitante.save()
        messages.success(request, f"Se ha registrado el fallecimiento de {habitante.nombres} {habitante.apellidos}.")
    
    return response    # =========================================================
    # SOLO SI EL PDF SE GENERÓ CORRECTAMENTE, GUARDAR EN BD
    # =========================================================
    habitante.vivo = False
    habitante.fecha_fallecimiento = fecha_fallecimiento
    habitante.hora_fallecimiento = hora_fallecimiento
    habitante.causa_fallecimiento = causa_fallecimiento
    habitante.save()
    
    messages.success(request, f"Se ha registrado el fallecimiento de {habitante.nombres} {habitante.apellidos}.")
    
    # Entregar el PDF al usuario
    response = HttpResponse(result.getvalue(), content_type='application/pdf')
    filename = f"constancia_fallecimiento_{habitante.id}_{fecha_fallecimiento}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response

# ====================================================================================
# FUNCIÓN AUXILIAR PARA CONVERTIR NÚMEROS A LETRAS (residencia)
# ====================================================================================
def numero_a_letras_residencia(n):
    if n == 0: return "cero"
    if n == 1: return "un"
    if n == 2: return "dos"
    if n == 3: return "tres"
    if n == 4: return "cuatro"
    if n == 5: return "cinco"
    if n == 6: return "seis"
    if n == 7: return "siete"
    if n == 8: return "ocho"
    if n == 9: return "nueve"
    if n == 10: return "diez"
    if n == 11: return "once"
    if n == 12: return "doce"
    if n == 13: return "trece"
    if n == 14: return "catorce"
    if n == 15: return "quince"
    if n == 16: return "dieciseis"
    if n == 17: return "diecisiete"
    if n == 18: return "dieciocho"
    if n == 19: return "diecinueve"
    if n == 20: return "veinte"
    if 21 <= n <= 29:
        return "veinti" + ("ún" if n == 21 else numero_a_letras_residencia(n - 20))
    if n == 30: return "treinta"
    if 31 <= n <= 39:
        return "treinta y " + numero_a_letras_residencia(n - 30)
    if n == 40: return "cuarenta"
    if 41 <= n <= 49:
        return "cuarenta y " + numero_a_letras_residencia(n - 40)
    if n == 50: return "cincuenta"
    if 51 <= n <= 59:
        return "cincuenta y " + numero_a_letras_residencia(n - 50)
    if n == 60: return "sesenta"
    if 61 <= n <= 69:
        return "sesenta y " + numero_a_letras_residencia(n - 60)
    if n == 70: return "setenta"
    if 71 <= n <= 79:
        return "setenta y " + numero_a_letras_residencia(n - 70)
    if n == 80: return "ochenta"
    if 81 <= n <= 89:
        return "ochenta y " + numero_a_letras_residencia(n - 80)
    if n == 90: return "noventa"
    if 91 <= n <= 99:
        return "noventa y " + numero_a_letras_residencia(n - 90)
    return str(n)


def obtener_voceros_firmantes():
    """Función auxiliar para obtener los voceros firmantes"""
    def obtener_firmante(comite_codigo):
        vocero = Voceria.objects.filter(comite_codigo=comite_codigo, tipo_vocero='VOCERO').first()
        if vocero:
            return vocero.habitante
        subvocero = Voceria.objects.filter(comite_codigo=comite_codigo, tipo_vocero='SUBVOCERO').first()
        if subvocero:
            return subvocero.habitante
        return None
    
    vivienda = obtener_firmante('VIVIENDA')
    servicios = obtener_firmante('SERVICIOS')
    salud = obtener_firmante('SALU')
    
    faltantes = []
    if not vivienda:
        faltantes.append("Vivienda y Hábitat")
    if not servicios:
        faltantes.append("Servicios Públicos")
    if not salud:
        faltantes.append("Salud Integral")
    
    return vivienda, servicios, salud, faltantes

# ====================================================================================
# --- CARTA DE BUENA CONDUCTA ---
# ====================================================================================
@login_required(login_url='login')
def carta_buena_conducta(request, habitante_id):
    """
    Genera la Carta de Buena Conducta para un habitante
    """
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    habitante = get_object_or_404(Habitante, id=habitante_id)
    
    # =========================================================
    # CONTADOR PARA CARTA DE BUENA CONDUCTA
    # =========================================================
    contador, created = ContadorConstancia.objects.get_or_create(
        tipo='buena_conducta',
        defaults={'ultimo_numero': 0}
    )
    nuevo_numero = contador.ultimo_numero + 1
    contador.ultimo_numero = nuevo_numero
    contador.save()
    
    # =========================================================
    # FECHA FORMATEADA
    # =========================================================
    hoy = date.today()
    dia = hoy.day
    mes = obtener_nombre_mes(hoy.month)  # "enero", "febrero", etc.
    anio = hoy.year
    
    # =========================================================
    # DATOS DEL HABITANTE
    # =========================================================
    es_mayor = habitante.edad >= 18
    edad_texto = "mayor de edad" if es_mayor else "menor de edad"
    nacionalidad_texto = "Venezolano(a)" if habitante.nacionalidad == 'V' else "Extranjero(a)"
    tiene_cedula = bool(habitante.cedula and habitante.cedula.strip())
    
    if tiene_cedula:
        documento_texto = f"titular de la cédula de identidad Nº {habitante.cedula_formateada}"
    else:
        documento_texto = "quien no posee cédula de identidad"
    
    ubicacion = habitante.get_calle_sector_display()
    
    # Tiempo de residencia en letras
    delta = relativedelta(hoy, habitante.fecha_ingreso)
    años = delta.years
    meses_delta = delta.months
    dias_delta = delta.days
    
    if años == 0 and meses_delta == 0:
        tiempo = f"{numero_a_letras(dias_delta)} {'días' if dias_delta != 1 else 'día'}"
    elif años >= 10:
        tiempo = f"{numero_a_letras(años)} años"
    elif años > 0 and meses_delta > 0:
        tiempo = f"{numero_a_letras(años)} {'años' if años > 1 else 'año'} y {numero_a_letras(meses_delta)} {'meses' if meses_delta > 1 else 'mes'}"
    elif años > 0:
        tiempo = f"{numero_a_letras(años)} {'años' if años > 1 else 'año'}"
    else:
        tiempo = f"{numero_a_letras(meses_delta)} {'meses' if meses_delta > 1 else 'mes'}"
    
    # =========================================================
    # OBTENER VOCEROS FIRMANTES
    # =========================================================
    def obtener_firmante(comite_codigo):
        vocero = Voceria.objects.filter(comite_codigo=comite_codigo, tipo_vocero='VOCERO').first()
        if vocero:
            return vocero.habitante
        subvocero = Voceria.objects.filter(comite_codigo=comite_codigo, tipo_vocero='SUBVOCERO').first()
        if subvocero:
            return subvocero.habitante
        return None
    
    firmante_vivienda = obtener_firmante('VIVIENDA')
    firmante_servicios = obtener_firmante('SERVICIOS')
    firmante_salud = obtener_firmante('SALU')
    
    voceros_faltantes = []
    if not firmante_vivienda:
        voceros_faltantes.append("Vivienda y Hábitat")
    if not firmante_servicios:
        voceros_faltantes.append("Servicios Públicos")
    if not firmante_salud:
        voceros_faltantes.append("Salud Integral")
    
    if voceros_faltantes:
        return render(request, 'comunidad/error_voceros.html', {
            'faltantes': voceros_faltantes,
            'habitante_id': habitante_id,
            'tipo': 'buena_conducta'
        })
    
    # =========================================================
    # MOTIVO (desde GET)
    # =========================================================
    motivo = request.GET.get('motivo', 'No especificado').upper()
    
    # =========================================================
    # CONTEXTO PARA EL TEMPLATE
    # =========================================================
    contexto = {
        # Número de constancia
        'numero_constancia': nuevo_numero,
        
        # Datos del habitante
        'apellido': habitante.apellidos.title(),
        'nombre': habitante.nombres.title(),
        'nacionalidad_texto': nacionalidad_texto,
        'edad_texto': edad_texto,
        'documento_texto': documento_texto,
        'ubicacion': ubicacion,
        'tiempo': tiempo,
        'motivo': motivo,
        
        # Fecha
        'dia': dia,
        'mes': mes,
        'anio': anio,
        
        # Vocero Vivienda
        'v_vivienda': f"{firmante_vivienda.nombres.title()} {firmante_vivienda.apellidos.title()}",
        'ci_vivienda': firmante_vivienda.cedula_formateada,
        'tel_vivienda': firmante_vivienda.telefono if firmante_vivienda.telefono else "No posee",
        
        # Vocero Servicios
        'v_servicios': f"{firmante_servicios.nombres.title()} {firmante_servicios.apellidos.title()}",
        'ci_servicios': firmante_servicios.cedula_formateada,
        'tel_servicios': firmante_servicios.telefono if firmante_servicios.telefono else "No posee",
        
        # Vocero Salud
        'v_salud': f"{firmante_salud.nombres.title()} {firmante_salud.apellidos.title()}",
        'ci_salud': firmante_salud.cedula_formateada,
        'tel_salud': firmante_salud.telefono if firmante_salud.telefono else "No posee",
        
        # Rutas de imágenes
        'escudoPath': settings.STATIC_URL + 'img/escudo_nacional.jpeg',
        'consejologoPath': settings.STATIC_URL + 'img/logo_comunas.jpeg',
    }
    
    # =========================================================
    # GENERAR PDF CON MARCA DE AGUA
    # =========================================================
    template = get_template('comunidad/carta_buena_conducta.html')
    html = template.render(contexto)
    
    filename = f"carta_buena_conducta_{habitante.id}"
    return generar_pdf_con_marca(html, filename, mostrar_en_navegador=True)
