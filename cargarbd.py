import os
import sys
import django
import random
from datetime import date, timedelta

# 1. Configura dinámicamente el settings de Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def encontrar_settings():
    for root, dirs, files in os.walk('.'):
        if 'settings.py' in files:
            package_name = os.path.basename(root)
            if package_name not in ['venv', '.git', '__pycache__', '.']:
                return f"{package_name}.settings"
    return None

settings_module = encontrar_settings()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
django.setup()

from comunidad.models import Habitante, Voceria, CensoBombona, JefeCalle, Proyecto, NotaSeguimiento, MovimientoFinanciero

def ejecutar_carga():
    # =========================================================
    # LISTA DE NOMBRES Y APELLIDOS REALISTAS
    # =========================================================
    nombres_hombres = [
        "Luis", "Carlos", "José", "Juan", "Pedro", "Miguel", "Jesús", "Manuel", "Antonio", "Francisco",
        "Jorge", "Alejandro", "Ricardo", "Andrés", "Fernando", "Gabriel", "Daniel", "Eduardo", "Sergio", "David",
        "Rafael", "Martín", "Pablo", "Víctor", "Raúl", "Alberto", "Mario", "Oscar", "Iván", "Héctor"
    ]
    
    nombres_mujeres = [
        "María", "Juana", "Ana", "Luz", "Carmen", "Martha", "Rosa", "Yolanda", "Patricia", "Sandra",
        "Elizabeth", "Cecilia", "Gloria", "Francisca", "Mónica", "Andrea", "Fernanda", "Daniela", "Verónica", "Teresa",
        "Carolina", "Paola", "Adriana", "Valentina", "Camila", "Isabella", "Gabriela", "Laura", "Diana", "Claudia"
    ]
    
    apellidos_comunes = [
        "González", "Rodríguez", "Pérez", "García", "Martínez", "Sánchez", "López", "Díaz", "Hernández", "Torres",
        "Flores", "Rivera", "Gómez", "Rojas", "Morales", "Ramírez", "Castro", "Ortega", "Vargas", "Silva",
        "Mendoza", "Castillo", "Vega", "Cordero", "Campos", "Navarro", "Reyes", "Paredes", "Maldonado", "Jiménez"
    ]
    
    # =========================================================
    # CONFIGURACIÓN - CALLES EXACTAS DEL MODELO
    # =========================================================
    calles = [
        'Monjas I',
        'Monjas II',
        'Vía club Sucre',
        'Entrada Km5 vía la amistad'
    ]
    
    puntos_referencia = [
        "Cerca de la escuela Bolivariana",
        "Al lado del módulo policial",
        "Frente a la cancha deportiva",
        "Esquina con la bodega Don José",
        "Detrás de la iglesia San Judas",
        "A 50 metros del centro de salud",
        "Junto al tanque de agua comunitario",
        "Diagonal al parque infantil",
        "Casa color verde cerca del puente",
        "Final de la calle, terreno número 8",
        "Al fondo del callejón, puerta blanca",
        "Referencia: antigua panadería La Fama",
        "Diagonal al centro espiritista",
        "Frente a la tienda esoterica",
        "Final del callejón de los gatos",
        "Mas abajo de doña Encarnación"
        "Diagonal a la cauchera",
        "20 metros antes del pool",
        "Diagonal a los gasolineros",
        "Cerca de la venta de repuestos nueva",
        "Cerca del abasto "
    ]
    
    discapacidades = [
        "", "", "", "", "",
        "Ninguna",
        "Movilidad reducida (uso de silla de ruedas)",
        "Discapacidad visual parcial",
        "Discapacidad auditiva (uso de audífonos)",
        "Problemas cardíacos controlados",
        "Hipertensión controlada",
        "Diabetes tipo 2",
        "Artritis severa",
        "Gastritis",
        "Sistitis",
        "Fingidas",
        "Ninguna", "Ninguna", "Ninguna"
    ]
    
    # =========================================================
    # PARENTESCOS VÁLIDOS (SOLO LOS QUE EXISTEN EN EL MODELO)
    # =========================================================
    # ✅ CORREGIDO: Usamos SOLO los parentescos que existen en PARENTESCO_CHOICES
    parentescos_validos = ['ESPOSO', 'HIJO', 'PADRE', 'HERMANO', 'NIETO', 'OTRO']
    
    # Mapeo de parentesco a género (para elegir nombres correctos)
    genero_por_parentesco = {
        'ESPOSO': 'M',
        'HIJO': 'M',
        'PADRE': 'M',
        'HERMANO': 'M',
        'NIETO': 'M',
        'OTRO': None,  # Aleatorio
    }
    
    # =========================================================
    # OBTENER CÓDIGOS DE COMITÉS
    # =========================================================
    codigos_comites = [c[0] for c in Voceria.COMITES]
    
    # =========================================================
    # PARÁMETROS DE CARGA
    # =========================================================
    MAX_PERSONAS_TOTAL = 100
    NUM_JEFES = 50
    
    print(f"🚀 Iniciando carga masiva con {MAX_PERSONAS_TOTAL} personas...")
    print("=" * 60)
    print(f"📌 Calles disponibles: {', '.join(calles)}")
    print("=" * 60)
    
    # Limpiar datos existentes
    print("\n🧹 Limpiando datos existentes...")
    MovimientoFinanciero.objects.all().delete()
    NotaSeguimiento.objects.all().delete()
    Proyecto.objects.all().delete()
    CensoBombona.objects.all().delete()
    JefeCalle.objects.all().delete()
    Voceria.objects.all().delete()
    Habitante.objects.all().delete()
    print("✅ Datos anteriores eliminados.\n")
    
    # =========================================================
    # 1. CREAR JEFES DE FAMILIA
    # =========================================================
    jefes_creados = []
    total_personas = 0
    
    print(f"📋 Creando {NUM_JEFES} jefes de familia...\n")
    
    for i in range(1, NUM_JEFES + 1):
        if total_personas >= MAX_PERSONAS_TOTAL:
            break
        
        nacionalidad = random.choices(['V', 'E'], weights=[75, 25])[0]
        # ✅ CORREGIDO: SOLO el número, sin la letra
        cedula_j = str(random.randint(1000000, 99999999))
        fecha_nac = date(random.randint(1960, 1995), random.randint(1, 12), random.randint(1, 28))
        
        genero = random.choice(['M', 'F'])
        nombre = random.choice(nombres_hombres if genero == 'M' else nombres_mujeres)
        apellido = random.choice(apellidos_comunes)
        calle_asignada = random.choice(calles)
        punto_ref = random.choice(puntos_referencia)
        discapacidad = random.choice(discapacidades)
        
        jefe = Habitante.objects.create(
            nacionalidad=nacionalidad,
            cedula=cedula_j,
            nombres=nombre,
            apellidos=apellido,
            fecha_nacimiento=fecha_nac,
            fecha_ingreso=date.today() - timedelta(days=random.randint(30, 3650)),
            genero=genero,
            telefono=f"0412-{random.randint(1000000, 9999999)}",
            calle_sector=calle_asignada,
            parentesco='JEFE',
            punto_referencia=punto_ref,
            discapacidad=discapacidad if discapacidad else "",
            jefe_familia=None,
            vivo=True,
            fecha_fallecimiento=None,
            hora_fallecimiento=None,
            causa_fallecimiento=None,
        )
        
        print(f"👑 JEFE #{i}: {nombre} {apellido} ({nacionalidad}) | Cédula: {jefe.cedula_formateada} | Calle: {calle_asignada}")
        print(f"   📍 Punto ref: {punto_ref}")
        jefes_creados.append(jefe)
        total_personas += 1
        
        # Agregar familiares (entre 0 y 3 por jefe)
        espacio_restante = MAX_PERSONAS_TOTAL - total_personas
        max_familiares = min(random.randint(0, 3), espacio_restante)
        
        for j in range(max_familiares):
            # ✅ CORREGIDO: SOLO el número, sin la letra
            cedula_fam = str(random.randint(1000000, 99999999))
            
            # ✅ CORREGIDO: Elegir SOLO de los parentescos válidos
            parentesco_elegido = random.choice(parentescos_validos)
            
            # Determinar género según parentesco
            gen_fam = genero_por_parentesco.get(parentesco_elegido)
            if gen_fam is None:  # Para 'OTRO'
                gen_fam = random.choice(['M', 'F'])
            
            # Elegir nombre según género
            nom_fam = random.choice(nombres_hombres if gen_fam == 'M' else nombres_mujeres)
            
            fecha_nac_fam = date(random.randint(1970, 2015), random.randint(1, 12), random.randint(1, 28))
            nacionalidad_fam = random.choices(['V', 'E'], weights=[75, 25])[0]
            discapacidad_fam = random.choice(discapacidades)
            
            familiar = Habitante.objects.create(
                nacionalidad=nacionalidad_fam,
                cedula=cedula_fam,
                nombres=nom_fam,
                apellidos=apellido,
                fecha_nacimiento=fecha_nac_fam,
                fecha_ingreso=date.today() - timedelta(days=random.randint(1, 1500)),
                genero=gen_fam,
                telefono=f"0424-{random.randint(1000000, 9999999)}" if random.random() > 0.3 else "",
                calle_sector=calle_asignada,
                parentesco=parentesco_elegido,
                punto_referencia=punto_ref if random.random() > 0.5 else random.choice(puntos_referencia),
                discapacidad=discapacidad_fam if discapacidad_fam else "",
                jefe_familia=jefe,
                vivo=True,
                fecha_fallecimiento=None,
                hora_fallecimiento=None,
                causa_fallecimiento=None,
            )
            print(f"   👤 {parentesco_elegido}: {nom_fam} {apellido} | Cédula: {familiar.cedula_formateada}")
            total_personas += 1
        
        print(f"✅ Procesado. (Total: {total_personas}/{MAX_PERSONAS_TOTAL})\n")
    
    # =========================================================
    # 2. CREAR VOCERÍAS
    # =========================================================
    print("\n" + "=" * 60)
    print("🎤 ASIGNANDO VOCERÍAS...")
    print("=" * 60)
    
    jefes_disponibles = list(Habitante.objects.filter(parentesco='JEFE'))
    random.shuffle(jefes_disponibles)
    
    vocero_index = 0
    for codigo, nombre_comite in Voceria.COMITES:
        if vocero_index < len(jefes_disponibles):
            vocero = jefes_disponibles[vocero_index]
            Voceria.objects.get_or_create(
                comite_codigo=codigo,
                tipo_vocero='VOCERO',
                defaults={'habitante': vocero}
            )
            print(f"🎤 VOCERO {nombre_comite}: {vocero.nombres} {vocero.apellidos} ({vocero.cedula_formateada})")
            vocero_index += 1
        
        if vocero_index < len(jefes_disponibles):
            subvocero = jefes_disponibles[vocero_index]
            Voceria.objects.get_or_create(
                comite_codigo=codigo,
                tipo_vocero='SUBVOCERO',
                defaults={'habitante': subvocero}
            )
            print(f"📢 SUBVOCERO {nombre_comite}: {subvocero.nombres} {subvocero.apellidos} ({subvocero.cedula_formateada})")
            vocero_index += 1
    
    # =========================================================
    # 3. JEFES DE CALLE
    # =========================================================
    print("\n" + "=" * 60)
    print("🏘️ ASIGNANDO JEFES DE CALLE...")
    print("=" * 60)
    
    for calle in calles:
        jefe_calle = Habitante.objects.filter(calle_sector=calle, parentesco='JEFE').first()
        if not jefe_calle and jefes_disponibles:
            jefe_calle = random.choice(jefes_disponibles)
        
        if jefe_calle:
            JefeCalle.objects.get_or_create(
                calle_nombre=calle,
                defaults={'habitante': jefe_calle}
            )
            print(f"🏠 Jefe de {calle}: {jefe_calle.nombres} {jefe_calle.apellidos} ({jefe_calle.cedula_formateada})")
    
    # =========================================================
    # 4. CENSO DE BOMBONAS DE GAS
    # =========================================================
    print("\n" + "=" * 60)
    print("⛽ REGISTRANDO CENSO DE BOMBONAS DE GAS...")
    print("=" * 60)
    
    for jefe in Habitante.objects.filter(parentesco='JEFE'):
        CensoBombona.objects.get_or_create(
            jefe_familia=jefe,
            defaults={
                'bombonas_10kg': random.randint(0, 5),
                'bombonas_18kg': random.randint(0, 4),
                'bombonas_27kg': random.randint(0, 3),
                'bombonas_43kg': random.randint(0, 2),
            }
        )
    
    censo_count = CensoBombona.objects.count()
    print(f"⛽ Censo de bombonas completado para {censo_count} familias")
    
    total_bombonas = sum([c.total_cilindros for c in CensoBombona.objects.all()])
    print(f"📊 Total de cilindros de gas registrados: {total_bombonas}")
    
    # =========================================================
    # 5. PROYECTOS COMUNITARIOS
    # =========================================================
    print("\n" + "=" * 60)
    print("🏗️ CREANDO PROYECTOS COMUNITARIOS...")
    print("=" * 60)
    
    proyectos_data = [
        ("Estadio Comunal", 35000, "Cancha sintética y graderíos para la comunidad"),
        ("Acueducto Rural", 42000, "Tuberías y tanque de almacenamiento de agua potable"),
        ("Casa de la Mujer", 15000, "Atención a víctimas de violencia de género"),
        ("Parque de la Familia", 8000, "Áreas verdes y juegos infantiles inclusivos"),
        ("Mercado Popular", 28000, "Puestos de comida y ventas para emprendedores"),
        ("Planta de Reciclaje", 45000, "Maquinaria y contenedores para reciclaje comunitario"),
        ("Farmacia Comunal", 12000, "Medicamentos esenciales y consultorio básico"),
        ("Guardería Infantil", 20000, "Cuidado y educación inicial para niños"),
        ("Centro de Capacitación", 18000, "Talleres de oficio y formación laboral"),
        ("Casa de la Cultura", 15000, "Biblioteca comunitaria y sala de cine"),
        ("Policlínico", 60000, "Atención médica 24h con especialistas"),
        ("Cementerio Municipal", 25000, "Ampliación de nichos y áreas verdes"),
        ("Cancha Múltiple", 12000, "Cancha de baloncesto, voleibol y fútbol sala"),
        ("Comedor Popular", 10000, "Comida gratuita para adultos mayores y niños"),
    ]
    
    proyectos_creados = []
    for nombre_proy, monto, desc in proyectos_data:
        comite_elegido = random.choice(codigos_comites)
        proyecto = Proyecto.objects.create(
            nombre=nombre_proy,
            comite=comite_elegido,
            recursos_usd=monto,
            descripcion=desc,
            estado=random.choice(['APROBADO', 'EN_EJECUCION', 'CULMINADO']),
            es_compromiso=random.choice([True, False]),
            ente_financista=random.choice(["Fondo Comunal", "Alcaldía", "Gobierno Nacional", "ONG Desarrollo Comunitario", "Cooperativa Local"]),
            ejecutor=random.choice(["Constructora Élite", "Arquitectos Asociados SA", "Ingeniería Solidaria", "Mano Propia Comunitaria"]),
            fecha_inicio_real=date.today() - timedelta(days=random.randint(0, 180)) if random.random() > 0.3 else None,
            fecha_cierre_real=date.today() - timedelta(days=random.randint(0, 30)) if random.random() > 0.6 else None,
        )
        proyectos_creados.append(proyecto)
        
        for _ in range(random.randint(1, 3)):
            NotaSeguimiento.objects.create(
                proyecto=proyecto,
                observacion=random.choice([
                    "Reunión de planificación con la comunidad aprobada",
                    "Licitación de materiales publicada",
                    "Avance de obra: 30% completado",
                    "Inspección técnica realizada sin observaciones",
                    "Inauguración oficial con presencia de voceros",
                    "Fondos liberados por contraloría",
                    "Manifestación de vecinos resuelta con diálogo",
                    "Entrega de primera fase a la comunidad",
                    "Capacitación a beneficiarios completada"
                ]),
                usuario_registro=random.choice([j.nombres for j in jefes_disponibles[:15]] if jefes_disponibles else ["Administrador"])
            )
        print(f"🏗️ Proyecto: {nombre_proy} | ${monto:,.2f} USD | Estado: {proyecto.estado}")
    
    # =========================================================
    # 6. MOVIMIENTOS FINANCIEROS
    # =========================================================
    print("\n" + "=" * 60)
    print("💰 REGISTRANDO MOVIMIENTOS FINANCIEROS COMUNALES...")
    print("=" * 60)
    
    monedas = ['USD', 'BS', 'COP']
    tipos = ['INGRESO', 'EGRESO']
    usuarios = [f"{j.nombres} {j.apellidos}" for j in jefes_disponibles[:20]] if jefes_disponibles else ["Administrador Comunal"]
    
    conceptos_serios = [
        "Aporte voluntario de habitantes",
        "Recaudación de fondos comunitarios",
        "Pago de servicios públicos (agua, luz, gas)",
        "Compra de materiales para proyecto",
        "Donación de comercio local",
        "Pago de mano de obra calificada",
        "Mantenimiento de infraestructura comunal",
        "Inscripción de nuevos habitantes al censo",
        "Fondo de emergencia comunitaria",
        "Pago de impuesto municipal",
        "Subsidio gubernamental recibido",
        "Transferencia entre comités",
        "Compra de equipamiento deportivo",
        "Gastos administrativos del comité",
        "Pago a proveedores de bombonas de gas",
        "Honorarios profesionales (abogado, contador)",
        "Actividad cultural y recreativa",
        "Capacitación y talleres formativos",
        "Ayuda humanitaria a familia vulnerable",
        "Mantenimiento de áreas verdes y aseo"
    ]
    
    num_movimientos = min(80, MAX_PERSONAS_TOTAL)
    ingresos = 0
    egresos = 0
    
    for _ in range(num_movimientos):
        moneda = random.choice(monedas)
        tipo = random.choice(tipos)
        
        if moneda == 'USD':
            monto = round(random.uniform(10, 8000), 2)
        elif moneda == 'BS':
            monto = round(random.uniform(500000, 80000000), 2)
        else:  # COP
            monto = round(random.uniform(20000, 800000), 2)
        
        if tipo == 'INGRESO':
            ingresos += monto if moneda == 'USD' else (monto / 40 if moneda == 'BS' else monto / 4000)
        else:
            egresos += monto if moneda == 'USD' else (monto / 40 if moneda == 'BS' else monto / 4000)
        
        MovimientoFinanciero.objects.create(
            tipo=tipo,
            concepto=random.choice(conceptos_serios),
            monto=monto,
            moneda=moneda,
            usuario_registrador=random.choice(usuarios)
        )
    
    print(f"💰 Movimientos registrados: {num_movimientos}")
    print(f"   📈 Ingresos totales (USD aprox): ${ingresos:,.2f}")
    print(f"   📉 Egresos totales (USD aprox): ${egresos:,.2f}")
    print(f"   💵 Balance (USD aprox): ${ingresos - egresos:,.2f}")
    
    # =========================================================
    # ESTADÍSTICAS FINALES
    # =========================================================
    print("\n" + "=" * 60)
    print("✅ ¡CARGA MASIVA COMPLETADA EXITOSAMENTE! ✅")
    print("=" * 60)
    
    total_habitantes = Habitante.objects.count()
    total_jefes = Habitante.objects.filter(parentesco='JEFE').count()
    total_familiares = total_habitantes - total_jefes
    
    print(f"\n📊 ESTADÍSTICAS DEL CENSO COMUNITARIO:")
    print(f"   • Habitantes censados: {total_habitantes}/{MAX_PERSONAS_TOTAL}")
    print(f"   • Jefes de familia: {total_jefes}")
    print(f"   • Familiares registrados: {total_familiares}")
    print(f"   • Vocerías ocupadas: {Voceria.objects.count()}")
    print(f"   • Jefes de Calle asignados: {JefeCalle.objects.count()}")
    print(f"   • Censo de bombonas: {CensoBombona.objects.count()}")
    print(f"   • Proyectos registrados: {Proyecto.objects.count()}")
    print(f"   • Notas de seguimiento: {NotaSeguimiento.objects.count()}")
    print(f"   • Movimientos financieros: {MovimientoFinanciero.objects.count()}")
    
    print(f"\n🏘️ DISTRIBUCIÓN POR CALLE/SECTOR:")
    for calle in calles:
        cantidad = Habitante.objects.filter(calle_sector=calle).count()
        print(f"   • {calle}: {cantidad} habitantes")
    
    venezolanos = Habitante.objects.filter(nacionalidad='V').count()
    extranjeros = Habitante.objects.filter(nacionalidad='E').count()
    print(f"\n🌍 NACIONALIDADES:")
    print(f"   • Venezolanos (V): {venezolanos} ({venezolanos*100//total_habitantes if total_habitantes else 0}%)")
    print(f"   • Extranjeros (E): {extranjeros} ({extranjeros*100//total_habitantes if total_habitantes else 0}%)")
    
    print("\n" + "=" * 60)
    print("🎉 ¡CENSO COMUNITARIO CARGADO EXITOSAMENTE! 🎉")
    print("=" * 60)

if __name__ == "__main__":
    ejecutar_carga()
