from django.db import models


class Habitante(models.Model):
    cedula = models.CharField(max_length=12, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField()
    calle_sector = models.CharField(max_length=100)
    enfermedad_cronica = models.TextField(null=True, blank=True)
    discapacidad = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.cedula} - {self.nombres}"
