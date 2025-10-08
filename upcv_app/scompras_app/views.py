from datetime import datetime, timezone
from venv import logger
from django.forms import IntegerField
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .form import PerfilForm, SolicitudCompraForm, UserCreateForm, UserEditForm, UserCreateForm, DepartamentoForm, UsuarioDepartamentoForm, InstitucionForm
from .models import Perfil, Departamento, UsuarioDepartamento, Institucion
from django.views.generic import CreateView
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.http import Http404, HttpResponseNotAllowed, JsonResponse
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db import models
from django.db.models import Sum, F, Value, Count, Q, Case, When, OuterRef, Subquery, IntegerField
from django.contrib.auth.decorators import login_required, user_passes_test
from collections import defaultdict
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
import json
from django.contrib.auth.models import Group
from .utils import grupo_requerido
from django.views.decorators.http import require_GET
from django.db.models.functions import Coalesce
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render
from django.template.loader import render_to_string
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from weasyprint import HTML
from django.db.models.functions import Cast, TruncWeek
from django.utils import timezone
from datetime import timedelta
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from decimal import Decimal
from datetime import datetime  
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font
import re

from django.core.mail import BadHeaderError
from smtplib import SMTPException

    
    
@login_required
@grupo_requerido('Administrador')
def editar_institucion(request):
    institucion = Institucion.objects.first()  # Solo debería haber una

    if request.method == 'POST':
        form = InstitucionForm(request.POST, request.FILES, instance=institucion)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos institucionales actualizados correctamente.")
            return redirect('scompras:editar_institucion')  # Reemplaza con la URL real
    else:
        form = InstitucionForm(instance=institucion)

    return render(request, 'scompras/editar_institucion.html', {'form': form})


@login_required
@grupo_requerido('Administrador', 'scompras')
@user_passes_test(lambda u: u.is_superuser or u.groups.filter(name='Administrador').exists())
def asignar_departamento_usuario(request):
    if request.method == 'POST':
        form = UsuarioDepartamentoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Departamento asignado correctamente al usuario.')
                return redirect('scompras:asignar_departamento')
            except:
                messages.error(request, 'Este usuario ya está asignado a ese departamento.')
    else:
        form = UsuarioDepartamentoForm()

    # Agrupar departamentos por usuario
    asignaciones = UsuarioDepartamento.objects.select_related('usuario', 'departamento')
    usuarios_con_departamentos = defaultdict(list)
    for asignacion in asignaciones:
        usuarios_con_departamentos[asignacion.usuario].append(asignacion.departamento)

    context = {
        'form': form,
        'usuarios_con_departamentos': usuarios_con_departamentos.items(),
    }
    return render(request, 'scompras/asignar_departamento.html', context)

def eliminar_asignacion(request, usuario_id, departamento_id):
    if request.method == 'POST':
        asignacion = get_object_or_404(UsuarioDepartamento, usuario_id=usuario_id, departamento_id=departamento_id)
        asignacion.delete()
        messages.success(request, 'Asignación eliminada correctamente.')
    else:
        messages.error(request, 'Método no permitido.')
    return redirect('scompras:asignar_departamento')


@login_required
def lista_departamentos(request):
    es_departamento = request.user.groups.filter(name='Departamento').exists()

    if es_departamento:
        # Obtener todos los objetos UsuarioDepartamento vinculados al usuario
        usuario_departamentos = UsuarioDepartamento.objects.filter(usuario=request.user)
        # Mostrar todos los departamentos asociados a esas instancias
        departamentos = Departamento.objects.filter(usuariodepartamento__in=usuario_departamentos)
    else:
        departamentos = Departamento.objects.all()

    return render(request, 'scompras/lista_departamentos.html', {
        'departamentos': departamentos,
        'es_departamento': es_departamento
    })

def acceso_denegado(request, exception=None):
    return render(request, 'scompras/403.html', status=403)

from django.db.models import Q



# Views for Departamento
@login_required
@grupo_requerido('Administrador', 'scompras')
def crear_departamento(request):
    departamentos = Departamento.objects.all()  # Obtener todos los departamentos
    form = DepartamentoForm(request.POST or None)  # Crear el formulario
    if form.is_valid():
        form.save()  # Guardar el nuevo departamento
        return redirect('scompras:crear_departamento')  # Redirige a la misma página para mostrar el nuevo departamento
    return render(request, 'scompras/crear_departamento.html', {'form': form, 'departamentos': departamentos})

@login_required
@grupo_requerido('Administrador', 'scompras')
def editar_departamento(request, pk):
    departamento = get_object_or_404(Departamento, pk=pk)  # Obtener el departamento por su PK
    form = DepartamentoForm(request.POST or None, instance=departamento)  # Rellenar el formulario con los datos existentes
    if form.is_valid():
        form.save()  # Guardar los cambios en el departamento
        return redirect('scompras:crear_departamento')  # Redirige a la vista de creación (o a donde desees)
    return render(request, 'scompras/editar_departamento.html', {'form': form, 'departamentos': Departamento.objects.all()})



@login_required
@grupo_requerido('Administrador', 'scompras')
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('new_password')
            user.set_password(password)
            user.save()

            group = form.cleaned_data.get('group')
            user.groups.add(group)

            # ✅ Espera a que la señal cree el perfil automáticamente
            foto = form.cleaned_data.get('foto')
            try:
                perfil = user.perfil  # accede al perfil creado por la señal
                if foto:
                    perfil.foto = foto
                    perfil.save()
            except Perfil.DoesNotExist:
                # Fallback solo si la señal falló (raro)
                Perfil.objects.create(user=user, foto=foto)

            messages.success(request, 'Usuario creado correctamente.')
            return redirect('scompras:user_create')
    else:
        form = UserCreateForm()

    users = User.objects.all()
    return render(request, 'scompras/user_form_create.html', {'form': form, 'users': users})

@login_required
@grupo_requerido('Administrador', 'scompras')
def user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    try:
        perfil = user.perfil
    except Perfil.DoesNotExist:
        perfil = Perfil(user=user)

    if request.method == 'POST':
        form_user = UserEditForm(request.POST, instance=user)
        form_perfil = PerfilForm(request.POST, request.FILES, instance=perfil)
        if form_user.is_valid() and form_perfil.is_valid():
            user = form_user.save(commit=False)
            user.save()

            # Actualizar grupo: limpiar y agregar el nuevo grupo
            group = form_user.cleaned_data.get('group')
            if group:
                user.groups.clear()
                user.groups.add(group)

            perfil = form_perfil.save(commit=False)
            perfil.user = user
            perfil.save()

            messages.success(request, 'Usuario editado correctamente.')
            return redirect('scompras:user_create')
    else:
        form_user = UserEditForm(instance=user)
        form_perfil = PerfilForm(instance=perfil)

    context = {
        'form': form_user,
        'perfil_form': form_perfil,
        'users': User.objects.all(),
    }
    return render(request, 'scompras/user_form_edit.html', context)



@login_required
@grupo_requerido('Administrador', 'scompras')
def perfil_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    try:
        perfil = user.perfil
    except Perfil.DoesNotExist:
        perfil = Perfil(user=user)
    
    if request.method == 'POST':
        form = PerfilForm(request.POST, request.FILES, instance=perfil)
        if form.is_valid():
            form.save()
            return redirect('scompras:user_edit', user_id=user.id)
    else:
        form = PerfilForm(instance=perfil)
    
    return render(request, 'scompras/perfil_edit.html', {'form': form, 'user': user})

@login_required
@grupo_requerido('Administrador', 'scompras')
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('scompras:user_create')  # Redirige a la misma página para mostrar la lista actualizada
    return render(request, 'scompras/user_confirm_delete.html', {'user': user})


def home(request):
    return render(request, 'scompras/login.html')

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum
import json

@login_required
@grupo_requerido('Administrador', 'scompras')
def dahsboard(request):



    return render(request, 'scompras/dashboard.html')



@login_required
def detalle_departamento(request, pk):
    departamento = get_object_or_404(Departamento, pk=pk)

    # Verificar si el usuario pertenece al departamento (opcional)
    if not UsuarioDepartamento.objects.filter(usuario=request.user, departamento=departamento).exists():
        return render(request, 'scompras/403.html', status=403)

    if request.method == 'POST':
        form = SolicitudCompraForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = request.user
            solicitud.departamento = departamento
            solicitud.save()
            return redirect('scompras:detalle_departamento', pk=departamento.pk)
    else:
        form = SolicitudCompraForm()

    return render(request, 'scompras/detalle_departamento.html', {
        'departamento': departamento,
        'form': form,
        'solicitudes': departamento.solicitudes.all().order_by('-fecha_solicitud'),
    })





    return render(request, 'scompras/detalle_departamento.html', {
        'departamento': departamento,
        'asignaciones_agrupadas': asignaciones_agrupadas,
        'asignaciones_detalle': asignaciones_detalle,
        'resumen_stock': resumen_stock,
        'tiene_acceso': tiene_acceso,
        'es_departamento': es_departamento,
        'departamentos': departamentos,
        'historial_transferencias': historial_transferencias,
    })


def signout(request):
    logout(request)
    return redirect('scompras:signin')


def signin(request):  
    institucion = Institucion.objects.first()
    if request.method == 'GET':
        # Deberías instanciar el AuthenticationForm correctamente
        return render(request, 'scompras/login.html', {
            'form': AuthenticationForm(),
            'institucion': institucion,
        })
    else:
        # Se instancia AuthenticationForm con los datos del POST para mantener el estado
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            # El método authenticate devuelve el usuario si es válido
            user = form.get_user()
            
            # Si el usuario es encontrado, se inicia sesión
            auth_login(request, user)
            
            # Ahora verificamos los grupos
            for g in user.groups.all():
                print(g.name)
                if g.name == 'Administrador':
                    return redirect('scompras:dahsboard')
                elif g.name == 'Departamento':
                    return redirect('scompras:crear_requerimiento')
                elif g.name == 'scompras':
                    return redirect('scompras:dahsboard')
            # Si no se encuentra el grupo adecuado, se redirige a una página por defecto
            return redirect('dahsboard')
        else:
            # Si el formulario no es válido, se retorna con el error
            return render(request, 'scompras/login.html', {
                'form': form,  # Pasamos el formulario con los errores
                'error': 'Usuario o contraseña incorrectos',
                'institucion': institucion,
            })



