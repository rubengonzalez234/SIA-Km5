from django.db import models
from django.utils import timezone

# ====================================================================================
# --- MÓDULO NUEVO: ESTRUCTURA DE COMITÉS ---
# ====================================================================================
class Comite(models.Model):
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Comité")
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")

    class Meta:
        verbose_name = "Comité"
        verbose_name_plural = "Comités"

    def __str__(self):
        return self.nombre


# ====================================================================================
# --- MÓDULO DE BASE DE DATOS REGISTRAL (HABITANTES) ---
# ====================================================================================
class Habitante(models.Model):
    PARENTESCO_CHOICES = [
        ('JEFE', 'Jefe de Familia'),
        ('ESPOSO', 'Esposo(a) / Conyugue'),
        ('HIJO', 'Hijo(a)'),
        ('PADRE', 'Padre / Madre'),
        ('HERMANO', 'Hermano(a)'),
        ('NIETO', 'Nieto(a)'),
        ('OTRO', 'Otro Familiar'),
    ]

    NACIONALIDAD_CHOICES = [
        ('V', 'Venezolano(a)'),
        ('E', 'Extranjero(a)'),
    ]

    GENERO_CHOICES = [
        ('M', 'Masculino (M)'),
        ('F', 'Femenino (F)'),
    ]

    CALLE_CHOICES = [
        ('Monjas I', 'Monjas I'),
        ('Monjas II', 'Monjas II'),
        ('Vía club Sucre', 'Vía club Sucre'),
        ('Entrada Km5 vía la amistad', 'Entrada Km5 vía la amistad'),
    ]

    nacionalidad = models.CharField(max_length=1, choices=NACIONALIDAD_CHOICES, default='V', verbose_name="Nacionalidad")
    cedula = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Cédula de Identidad")
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    fecha_ingreso = models.DateField(
        verbose_name="Radicado desde",
        null=False, 
        blank=False
    )
    genero = models.CharField(max_length=1, choices=GENERO_CHOICES, verbose_name="Género")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono de Contacto")
    calle_sector = models.CharField(max_length=50, choices=CALLE_CHOICES, verbose_name="Calle / Sector")
    parentesco = models.CharField(max_length=20, choices=PARENTESCO_CHOICES, verbose_name="Parentesco con el Jefe de Familia")
    
    punto_referencia = models.TextField(blank=True, null=True, verbose_name="Punto de Referencia")
    discapacidad = models.CharField(max_length=100, blank=True, null=True, verbose_name="Discapacidad")
    jefe_familia = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='familiares', verbose_name="Jefe de Familia Relacionado")
    
    # =========================================================
    # NUEVOS CAMPOS PARA CONTROL DE FALLECIMIENTO
    # =========================================================
    vivo = models.BooleanField(default=True, verbose_name="¿Está vivo?")
    fecha_fallecimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Fallecimiento")
    hora_fallecimiento = models.CharField(max_length=50, null=True, blank=True, verbose_name="Hora de Fallecimiento")
    causa_fallecimiento = models.TextField(null=True, blank=True, verbose_name="Causa de Fallecimiento")

    class Meta:
        verbose_name = "Habitante"
        verbose_name_plural = "Habitantes"

    def __str__(self):
        estado = "✝" if not self.vivo else ""
        return f"{estado} {self.nombres} {self.apellidos}"

    @property
    def cedula_formateada(self):
        if not self.cedula or self.cedula == 'None' or self.cedula.strip() == '':
            return "NO POSEE"
        return f"{self.nacionalidad}-{self.cedula}"

    @property
    def edad(self):
        import datetime
        today = datetime.date.today()
        return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))


# ====================================================================================
# --- MÓDULO DE ORGANIZACIÓN COMUNAL (VOCERÍAS / CALLES) ---
# ====================================================================================
class Voceria(models.Model):
    TIPOS_VOCERIA = [
        ('VOCERO', 'Vocero Principal'),
        ('SUBVOCERO', 'Subvocero / Suplente'),
    ]

    COMITES = [
        # ELIMINADO: ('EJECUTIVO', 'Unidad Ejecutiva'),
        ('FINANZAS', 'Unidad Administrativa y Financiera'),
        ('CONTRALORIA', 'Unidad de Contraloría Social'),
        ('VIVIENDA', 'Vivienda y Hábitat'),
        ('SERVICIOS', 'Servicios Públicos (Agua, Luz, Gas)'),
        ('SALU', 'Salud Integral'),
        ('ALIM', 'Alimentación y Defensa al Consumidor'),           # NUEVO
        ('ECON', 'Economía Comunal'),                               # EDITADO (sacamos "y Emprendimiento")
        ('EDUC', 'Educación, Cultura y Formación'),
        ('DEPO', 'Deporte y Recreación'),
        ('ECOS', 'Ecosocialismo'),                                 # EDITADO (era AMBI)
        ('PLAN', 'Planificación Comunal'),                         # NUEVO
        ('SEG', 'Seguridad y Defensa Integral'),                   # NUEVO
    ]

    habitante = models.ForeignKey(Habitante, on_delete=models.CASCADE, related_name='cargos_comunales', verbose_name="Habitante")
    comite_codigo = models.CharField(max_length=20, choices=COMITES, verbose_name="Comité / Unidad")
    tipo_vocero = models.CharField(max_length=15, choices=TIPOS_VOCERIA, verbose_name="Tipo de Vocería")
    fecha_asignacion = models.DateField(auto_now_add=True, verbose_name="Fecha de Asignación")

    class Meta:
        verbose_name = "Vocería"
        verbose_name_plural = "Vocerías"
        unique_together = ('comite_codigo', 'tipo_vocero')

    def __str__(self):
        return f"{self.tipo_vocero} - {self.get_comite_codigo_display()}"


class JefeCalle(models.Model):
    calle_nombre = models.CharField(max_length=50, choices=Habitante.CALLE_CHOICES, unique=True, verbose_name="Calle a Cargo")
    habitante = models.ForeignKey(Habitante, on_delete=models.CASCADE, related_name='jefaduras_calle', verbose_name="Jefe de Calle")
    fecha_asignacion = models.DateField(auto_now_add=True, verbose_name="Fecha de Designación")

    class Meta:
        verbose_name = "Jefe de Calle"
        verbose_name_plural = "Jefes de Calle"

    def __str__(self):
        return f"Jefe de {self.calle_nombre} - {self.habitante.nombres}"


# ====================================================================================
# --- MÓDULO DE SERVICIOS PÚBLICOS (CENSO DE GAS) ---
# ====================================================================================
class CensoBombona(models.Model):
    jefe_familia = models.OneToOneField(
        Habitante, 
        on_delete=models.CASCADE, 
        limit_choices_to={'parentesco': 'JEFE'}, 
        related_name='censo_gas',
        verbose_name="Jefe de Familia"
    )
    bombonas_10kg = models.PositiveIntegerField(default=0, verbose_name="Bombonas 10 Kg")
    bombonas_18kg = models.PositiveIntegerField(default=0, verbose_name="Bombonas 18 Kg")
    bombonas_27kg = models.PositiveIntegerField(default=0, verbose_name="Bombonas 27 Kg")
    bombonas_43kg = models.PositiveIntegerField(default=0, verbose_name="Bombonas 43 Kg")
    fecha_registro = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Gas - {self.jefe_familia.nombres} {self.jefe_familia.apellidos}"

    @property
    def total_cilindros(self):
        return self.bombonas_10kg + self.bombonas_18kg + self.bombonas_27kg + self.bombonas_43kg


# ====================================================================================
# --- MÓDULO DE GESTIÓN Y AUDITORÍA DE PROYECTOS COMUNITARIOS ---
# ====================================================================================
ESTADOS_PROYECTO = [
    ('APROBADO', 'Aprobado'),
    ('EN_EJECUCION', 'En Ejecución'),
    ('CULMINADO', 'Culminado'),
]

class Proyecto(models.Model):
    nombre = models.CharField(max_length=255)
    
    comite = models.CharField(
        max_length=50, 
        choices=Voceria.COMITES, 
        verbose_name="Comité / Categoría"
    )
    
    recursos_usd = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_aprobacion = models.DateField(default=timezone.now)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_PROYECTO, default='APROBADO')
    es_compromiso = models.BooleanField(default=True)
    ente_financista = models.CharField(max_length=150, blank=True, null=True)
    ejecutor = models.CharField(max_length=150, blank=True, null=True)
    fecha_inicio_real = models.DateField(blank=True, null=True)
    fecha_cierre_real = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class NotaSeguimiento(models.Model):
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, related_name='notas')
    fecha_registro = models.DateTimeField(default=timezone.now)
    observacion = models.TextField()
    usuario_registro = models.CharField(max_length=100)

    def __str__(self):
        return f"Nota {self.fecha_registro} - {self.proyecto.nombre}"


# ====================================================================================
# --- MÓDULO DE FINANZAS COMUNALES ---
# ====================================================================================
class MovimientoFinanciero(models.Model):
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso (+)'),
        ('EGRESO', 'Egreso (-)'),
    ]
    
    MONEDA_CHOICES = [
        ('USD', 'Dólares (USD)'),
        ('BS', 'Bolívares (BS)'),
        ('COP', 'Pesos Colombianos (COP)'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, verbose_name="Tipo de Movimiento")
    concepto = models.CharField(max_length=255, verbose_name="Concepto / Descripción")
    monto = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Monto")
    moneda = models.CharField(max_length=3, choices=MONEDA_CHOICES, default='USD', verbose_name="Moneda")
    fecha_registro = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Registro")
    usuario_registrador = models.CharField(max_length=150, verbose_name="Registrado por")

    class Meta:
        verbose_name = "Movimiento Financiero"
        verbose_name_plural = "Movimientos Financieros"

    def __str__(self):
        return f"{self.tipo} ({self.moneda}) - {self.concepto} - {self.monto}"


# ====================================================================================
# --- CONTADOR DE CONSTANCIAS ---
# ====================================================================================
class ContadorConstancia(models.Model):
    TIPO_CHOICES = [
        ('residencia', 'Constancia de Residencia'),
        ('comercial', 'Carta Aval Comercial'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, unique=True)
    ultimo_numero = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.get_tipo_display()}: {self.ultimo_numero}"
