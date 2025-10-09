from asyncio import open_connection
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.db.models import Sum
from django.db.models.signals import post_save
from django.utils import timezone

class Institucion(models.Model):
    nombre = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20)
    pagina_web = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    logo2 = models.ImageField(upload_to='logos/', blank=True, null=True)

    def __str__(self):
        return self.nombre


# Modelo de Departamento
class Departamento(models.Model):
    id_departamento = models.CharField(max_length=50, unique=True)  # ID personalizado del departamento
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # Fecha de creación automática
    fecha_actualizacion = models.DateTimeField(auto_now=True)  # Fecha de actualización automática
    activo = models.BooleanField(default=True) # Campo para determinar si el departamento está activo
    
    def __str__(self):
        return self.nombre
   
    
class Seccion(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name='secciones')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f'{self.nombre} ({self.departamento.nombre})'


class SolicitudCompra(models.Model):
    seccion = models.ForeignKey('Seccion', on_delete=models.CASCADE, related_name='solicitudes')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    descripcion = models.TextField()
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    aprobada = models.BooleanField(default=False)

    def __str__(self):
        return f'Solicitud #{self.id} - {self.seccion.nombre}'

    def get_absolute_url(self):
        return reverse('scompras:detalle_solicitud', kwargs={'pk': self.pk})


class UsuarioDepartamento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, null=True, blank=True)  # nuevo campo

    class Meta:
        unique_together = ('usuario', 'departamento', 'seccion')  # ahora la combinación incluye seccion

    def __str__(self):
        return f'{self.usuario.username} - {self.departamento.nombre} - {self.seccion.nombre if self.seccion else "Sin Sección"}'

 

class FraseMotivacional(models.Model):
    frase = models.CharField(max_length=500)
    personaje = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.personaje}: {self.frase}'
    


def user_directory_path(instance, filename):
    # El archivo se subirá a MEDIA_ROOT/perfil_usuario/<username>/<filename>
    return f'perfil_usuario/{instance.user.username}/{filename}'

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(upload_to=user_directory_path, null=True, blank=True)

    def __str__(self):
        return f'Perfil de {self.user.username}'

# Señal: Crear perfil automáticamente cuando se crea un usuario
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'perfil'):
        Perfil.objects.create(user=instance)

# Señal opcional: Guardar perfil cuando el usuario se guarda
@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    if hasattr(instance, 'perfil'):
        instance.perfil.save()
     
        

# Modelo de Insumo (para la importación de datos desde Excel)
class Insumo(models.Model):
    renglon = models.IntegerField()
    codigo_insumo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=500)
    caracteristicas = models.TextField(blank=True, null=True)
    nombre_presentacion = models.CharField(max_length=500)
    cantidad_unidad_presentacion = models.CharField(max_length=100)
    codigo_presentacion = models.CharField(max_length=100)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.codigo_insumo} - {self.nombre}"


# Modelo para la fecha de insumo (para la importación de datos desde Excel)
class FechaInsumo(models.Model):
    fechainsumo = models.DateField()  

    def __str__(self):
        return f"{self.fechainsumo}"        