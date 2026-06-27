from django.urls import path
from . import views

urlpatterns = [
    # --- SECCIÓN DE AUTENTICACIÓN (LOGIN ES INICIO) ---
    path('', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),

    # --- PÁGINA PRINCIPAL DEL MÓDULO (LISTADO CENSAL) ---
    path('habitantes/', views.lista_habitantes, name='lista_habitantes'),
    
    # --- SISTEMA DE CONTROL DE HABITANTES (CRUD VECINAL) ---
    path('nuevo/', views.crear_habitante, name='crear_habitante'),
    path('editar/<int:pk>/', views.editar_habitante, name='editar_habitante'),
    path('eliminar/<int:pk>/', views.eliminar_habitante, name='eliminar_habitante'),
    
    # --- MÓDULO DE ORGANIZACIÓN INFORMATIZACIONAL (ESTRUCTURA POLÍTICA) ---
    path('organizacion/', views.panel_organizacion, name='organizacion'),
    path('organizacion/asignar/', views.asignar_vocero, name='asignar_vocero'),
    path('organizacion/remover/', views.remover_vocero, name='remover_vocero'),
    
    # --- SECCIÓN DE REPORTES (PROCESAMIENTO A PDF) ---
    path('pdf/', views.exportar_censo_pdf, name='exportar_censo_pdf'),
    path('constancia/<int:habitante_id>/', views.generar_constancia_pdf, name='generar_constancia'),

    # --- JEFES DE CALLE ---
    path('organizacion/asignar-jefe/', views.asignar_jefe_calle, name='asignar_jefe_calle'),
    path('organizacion/remover-jefe/', views.remover_jefe_calle, name='remover_jefe_calle'),

    # --- MÓDULO DE CENSO DE BOMBONAS ---
    path('censo-bombonas/', views.censo_bombonas, name='censo_bombonas'),
    path('censo-bombonas/guardar/', views.guardar_bombonas, name='guardar_bombonas'),
    #PEDIDOS
    path('censo-gas/pdf/', views.exportar_bombonas_pdf, name='exportar_bombonas_pdf'),
    #CENSO
    path('censo-censo-gas/pdf/', views.exportar_censo_bombonas_pdf, name='exportar_censo_bombonas_pdf'),

    # --- MÓDULO DE PROYECTOS (INTEGRADO Y SIN ERRORES) ---
    path('proyectos/', views.lista_proyectos, name='lista_proyectos'),
    path('proyectos/avanzar/<int:proyecto_id>/', views.avanzar_fase_proyecto, name='avanzar_proyecto'),
    path('proyectos/nota/<int:proyecto_id>/', views.agregar_nota_proyecto, name='agregar_nota_proyecto'),
    path('proyectos/pdf/<int:proyecto_id>/', views.exportar_proyecto_pdf, name='exportar_proyecto_pdf'),
       # --- MÓDULO DE FINANZAS MULTIMONEDA OPERACIONAL (NUEVO) ---
    # Entrada general: /finanzas/ (Por defecto va a USD en la vista)
    path('finanzas/', views.panel_finanzas, {'moneda': 'USD'}, name='panel_finanzas'),
    # Filtro explícito de libros: /finanzas/USD/, /finanzas/BS/, /finanzas/COP/
    path('finanzas/<str:moneda>/', views.panel_finanzas, name='panel_finanzas_moneda'),
    # Procesamiento de formularios de carga contable según la moneda activa
    path('finanzas/guardar/<str:moneda>/', views.guardar_movimiento, name='guardar_movimiento'),
    # Exportación e impresión de reportes de auditoría por divisa aislada
    path('finanzas/pdf/<str:moneda>/', views.exportar_finanzas_pdf, name='exportar_finanzas_pdf'),

    #CLAP
    path('clap/', views.gestion_clap, name='gestion_clap'),
    path('clap/exportar-pdf/', views.exportar_clap_pdf, name='exportar_clap_pdf'),
    
    #CARTA AVAL
    path('carta-aval/<int:habitante_id>/', views.generar_carta_aval, name='generar_carta_aval'),
    # --- CONSTANCIA DE FALLECIMIENTO (NUEVA) ---
    path('constancia-fallecimiento/<int:habitante_id>/', views.generar_constancia_fallecimiento_pdf, name='constancia_fallecimiento'),
    #BUENA COND[UCTA
    path('carta-buena-conducta/<int:habitante_id>/', views.carta_buena_conducta, name='carta_buena_conducta'),
]
