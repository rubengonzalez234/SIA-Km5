from django.urls import path
from . import views

urlpatterns = [
    # Rutas de Autenticación y Home
    path('', views.home, name='home'),
    path('acceso/', views.login_usuario, name='login'),
    path('salir/', views.logout_usuario, name='logout'),
    
    # Rutas del Sistema de Habitantes (CRUD)
    path('habitantes/', views.lista_habitantes, name='lista_habitantes'),
    path('habitantes/nuevo/', views.crear_habitante, name='crear_habitante'),
    path('habitantes/editar/<int:pk>/', views.editar_habitante, name='editar_habitante'),
    
    # Cambio sugerido: 'eliminar_habitante' es más descriptivo para tus plantillas
    path('habitantes/eliminar/<int:pk>/', views.eliminar_habitante, name='eliminar_habitante'),
    
    # Reportes
    path('habitantes/pdf/', views.exportar_pdf, name='exportar_pdf'),
]

# El manejador de errores debe apuntar exactamente a la función en views.py
handler403 = 'comunidad.views.error_403'