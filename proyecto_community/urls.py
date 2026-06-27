"""proyecto_community URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from comunidad import views as comunidad_views

urlpatterns = [
    # Ruta de administración nativa de Django
    path('admin/', admin.site.urls), 
    
    # CORRECCIÓN: Apunta directamente a la lista de habitantes como pantalla de inicio principal
    path('', comunidad_views.lista_habitantes, name='home'),
    
    # Inclusión de las rutas específicas de la aplicación comunidad
    path('habitantes/', include('comunidad.urls')),
    
    # Rutas del módulo de autenticación y control de accesos
    path('login/', comunidad_views.login_usuario, name='login'),
    path('logout/', comunidad_views.logout_usuario, name='logout'),
]

#handler403 = 'comunidad.views.error_403'
