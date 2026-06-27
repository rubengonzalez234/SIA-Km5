#!/usr/bin/env python
"""
Script para BORRAR DATOS POR MÓDULOS en SIA KM5
Permite seleccionar qué módulos limpiar sin afectar el resto
"""

import os
import sys
import django

# Configurar la ruta del proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def encontrar_settings():
    """Busca automáticamente el archivo settings.py"""
    for root, dirs, files in os.walk('.'):
        if 'settings.py' in files:
            # Saltar carpetas de entorno virtual
            if 'venv' in root or 'env' in root or '.venv' in root:
                continue
            package_name = os.path.basename(root)
            if package_name and not package_name.startswith('.'):
                return f"{package_name}.settings"
    return None

settings_module = encontrar_settings()

if not settings_module:
    print("❌ Error: No se encontró el archivo settings.py")
    print("Asegúrate de ejecutar este script en la raíz de tu proyecto Django")
    sys.exit(1)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from comunidad.models import (
    Habitante, 
    Voceria, 
    JefeCalle, 
    CensoBombona, 
    Proyecto, 
    NotaSeguimiento, 
    MovimientoFinanciero,
    ContadorConstancia,
    Comite
)

User = get_user_model()

# ============================================================
# DEFINICIÓN DE MÓDULOS
# ============================================================
MODULOS = {
    '1': {
        'nombre': 'Habitantes (Censo)',
        'descripcion': 'Elimina todos los habitantes, incluyendo sus relaciones familiares',
        'modelos': ['Habitante'],
        'dependencias': ['Voceria', 'JefeCalle', 'CensoBombona']
    },
    '2': {
        'nombre': 'Vocerías',
        'descripcion': 'Elimina todas las vocerías y subvocerías',
        'modelos': ['Voceria'],
        'dependencias': []
    },
    '3': {
        'nombre': 'Jefes de Calle',
        'descripcion': 'Elimina todas las asignaciones de Jefes de Calle',
        'modelos': ['JefeCalle'],
        'dependencias': []
    },
    '4': {
        'nombre': 'Censo de Gas',
        'descripcion': 'Elimina todos los registros del censo de bombonas',
        'modelos': ['CensoBombona'],
        'dependencias': []
    },
    '5': {
        'nombre': 'Proyectos y Notas',
        'descripcion': 'Elimina todos los proyectos y sus notas de seguimiento',
        'modelos': ['NotaSeguimiento', 'Proyecto'],
        'dependencias': []
    },
    '6': {
        'nombre': 'Movimientos Financieros',
        'descripcion': 'Elimina todos los movimientos de ingresos y egresos',
        'modelos': ['MovimientoFinanciero'],
        'dependencias': []
    },
    '7': {
        'nombre': 'Contadores de Constancias',
        'descripcion': 'Reinicia los contadores de constancias a 0',
        'modelos': ['ContadorConstancia'],
        'dependencias': [],
        'es_contador': True
    },
    '8': {
        'nombre': 'Comités',
        'descripcion': 'Elimina todos los comités registrados',
        'modelos': ['Comite'],
        'dependencias': []
    },
    '9': {
        'nombre': 'TODO (Reset completo)',
        'descripcion': 'Elimina TODOS los datos del sistema (excepto usuarios)',
        'modelos': ['NotaSeguimiento', 'Proyecto', 'CensoBombona', 'JefeCalle', 'Voceria', 
                   'MovimientoFinanciero', 'Comite', 'Habitante', 'ContadorConstancia'],
        'dependencias': [],
        'es_todo': True
    }
}

def mostrar_menu():
    """Muestra el menú interactivo"""
    print("\n" + "=" * 70)
    print("   SIA KM5 - LIMPIEZA SELECTIVA DE DATOS")
    print("=" * 70)
    print("\nSelecciona el módulo que deseas limpiar:\n")
    
    for key, modulo in MODULOS.items():
        if key == '9':
            print(f"   {key}. {modulo['nombre']} ⚠️")
        else:
            print(f"   {key}. {modulo['nombre']}")
        print(f"      └─ {modulo['descripcion']}")
        print()
    
    print("   0. Salir sin hacer nada")
    print("\n" + "=" * 70)

def obtener_seleccion():
    """Obtiene la selección del usuario"""
    while True:
        seleccion = input("\n🔢 Ingresa el número del módulo a limpiar: ").strip()
        
        if seleccion == '0':
            return None
        
        if seleccion in MODULOS:
            return seleccion
        
        print("❌ Opción inválida. Por favor, selecciona un número válido.")

def confirmar_operacion(modulo):
    """Solicita confirmación antes de borrar"""
    print("\n" + "=" * 70)
    print(f"⚠️  ESTÁS A PUNTO DE BORRAR: {modulo['nombre']}")
    print("=" * 70)
    print(f"\n{modulo['descripcion']}")
    
    if modulo.get('es_todo'):
        print("\n🔴 ¡ATENCIÓN! Esto borrará TODOS los datos del sistema.")
        print("   Se mantendrán únicamente los usuarios administradores.")
    
    if modulo.get('dependencias'):
        print(f"\n📌 Este módulo tiene dependencias con: {', '.join(modulo['dependencias'])}")
        print("   Se recomienda limpiar también esos módulos para mantener consistencia.")
    
    print("\n" + "-" * 70)
    confirmacion = input("¿Estás seguro de continuar? (escribe 'SI' para confirmar): ")
    
    return confirmacion.strip().upper() == "SI"

def contar_registros(modelo):
    """Cuenta los registros de un modelo"""
    try:
        return modelo.objects.count()
    except:
        return 0

def limpiar_modulo(modulo_key):
    """Ejecuta la limpieza del módulo seleccionado"""
    modulo = MODULOS[modulo_key]
    
    print("\n" + "=" * 70)
    print(f"🔄 LIMPIANDO: {modulo['nombre']}")
    print("=" * 70)
    
    resultados = {}
    total_eliminados = 0
    
    for modelo_nombre in modulo['modelos']:
        try:
            # Obtener el modelo
            modelo = globals().get(modelo_nombre)
            if not modelo:
                print(f"   ⚠️ Modelo '{modelo_nombre}' no encontrado")
                continue
            
            # Contar antes
            cantidad = contar_registros(modelo)
            
            if cantidad == 0:
                print(f"   ℹ️ {modelo_nombre}: No hay registros para eliminar")
                resultados[modelo_nombre] = 0
                continue
            
            # Si es contador, reiniciar en lugar de eliminar
            if modulo.get('es_contador') or modelo_nombre == 'ContadorConstancia':
                # Reiniciar contadores
                for contador in modelo.objects.all():
                    contador.ultimo_numero = 0
                    contador.save()
                print(f"   ✅ {modelo_nombre}: {cantidad} contadores reiniciados a 0")
                resultados[modelo_nombre] = cantidad
                total_eliminados += cantidad
            else:
                # Eliminar registros
                modelo.objects.all().delete()
                print(f"   ✅ {modelo_nombre}: {cantidad} registros eliminados")
                resultados[modelo_nombre] = cantidad
                total_eliminados += cantidad
                
        except Exception as e:
            print(f"   ❌ Error al limpiar {modelo_nombre}: {str(e)}")
            resultados[modelo_nombre] = f"Error: {str(e)}"
    
    # Si es el módulo "TODO", verificar usuarios administradores
    if modulo.get('es_todo'):
        print("\n👤 Verificando usuarios administradores...")
        superusers = User.objects.filter(is_superuser=True)
        
        if superusers.exists():
            print(f"   ✅ Se mantendrá(n) el/los siguiente(s) usuario(s) administrador(es):")
            for user in superusers:
                print(f"      - {user.username} ({user.email or 'sin email'})")
        else:
            print("   ⚠️ No se encontró ningún usuario administrador.")
            crear_admin = input("\n¿Deseas crear un usuario administrador? (s/n): ")
            if crear_admin.lower() == 's':
                username = input("   Nombre de usuario: ")
                email = input("   Correo electrónico: ")
                password = input("   Contraseña: ")
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                print(f"   ✅ Usuario administrador '{username}' creado correctamente.")
        
        # Reiniciar contadores de constancias
        print("\n🔄 Reiniciando contadores de constancias...")
        ContadorConstancia.objects.get_or_create(
            tipo='residencia',
            defaults={'ultimo_numero': 0}
        )
        ContadorConstancia.objects.get_or_create(
            tipo='comercial',
            defaults={'ultimo_numero': 0}
        )
        print("   ✅ Contadores reiniciados a 0")
    
    # Reporte final
    print("\n" + "=" * 70)
    print(f"   📊 REPORTE DE LIMPIEZA - {modulo['nombre']}")
    print("=" * 70)
    print(f"\n   Total de registros afectados: {total_eliminados}")
    print("\n   Detalle:")
    for modelo_nombre, cantidad in resultados.items():
        print(f"      - {modelo_nombre}: {cantidad}")
    
    print("\n" + "=" * 70)
    print("   ✅ OPERACIÓN COMPLETADA")
    print("=" * 70)

# ============================================================
# FUNCIÓN PRINCIPAL - ¡ESTA ES LA QUE FALTABA!
# ============================================================
def main():
    """Función principal del script"""
    print("\n" + "=" * 70)
    print("   🏠 SISTEMA INTEGRADO DE ADMINISTRACIÓN - KM5")
    print("=" * 70)
    print("\n⚠️  Este script te permite limpiar datos de módulos específicos.")
    print("   Los datos eliminados NO se pueden recuperar.")
    
    while True:
        mostrar_menu()
        seleccion = obtener_seleccion()
        
        if seleccion is None:
            print("\n👋 Saliendo del script. ¡Hasta luego!")
            break
        
        modulo = MODULOS[seleccion]
        
        if confirmar_operacion(modulo):
            limpiar_modulo(seleccion)
            print("\n✅ Limpieza completada exitosamente.")
            
            # Preguntar si quiere limpiar otro módulo
            continuar = input("\n¿Deseas limpiar otro módulo? (s/n): ").strip().lower()
            if continuar != 's':
                print("\n👋 Saliendo del script. ¡Hasta luego!")
                break
        else:
            print("\n❌ Operación cancelada por el usuario.")
            continuar = input("\n¿Deseas intentar con otro módulo? (s/n): ").strip().lower()
            if continuar != 's':
                print("\n👋 Saliendo del script. ¡Hasta luego!")
                break

# ============================================================
# PUNTO DE ENTRADA DEL SCRIPT
# ============================================================
if __name__ == "__main__":
    main()
