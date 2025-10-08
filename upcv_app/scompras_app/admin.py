from django.contrib import admin
from .models import (
    Departamento,FraseMotivacional, 
    UsuarioDepartamento
)


class UsuarioDepartamentoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'departamento')
    search_fields = ('usuario__username', 'departamento__nombre')
    list_filter = ('departamento',)

admin.site.register(UsuarioDepartamento, UsuarioDepartamentoAdmin)


# Crea una clase que personaliza la vista en el admin
class FraseMotivacionalAdmin(admin.ModelAdmin):
    list_display = ('frase', 'personaje')  # Qué campos mostrar en la lista
    search_fields = ('frase', 'personaje')  # Habilitar búsqueda por estos campos
    ordering = ('personaje',)  # Ordenar por el campo 'personaje'

admin.site.register(FraseMotivacional, FraseMotivacionalAdmin)

# Registrar Departamento
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('id_departamento', 'nombre', 'descripcion', 'fecha_creacion', 'fecha_actualizacion')
    search_fields = ('nombre', 'id_departamento')
    list_filter = ('fecha_creacion', 'fecha_actualizacion')

admin.site.register(Departamento, DepartamentoAdmin)



