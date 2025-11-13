from datetime import datetime, timezone
from django.utils.timezone import localtime
from venv import logger
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.forms import IntegerField
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import openpyxl
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
from .form import ExcelUploadForm, SeccionForm, FechaInsumoForm, PerfilForm, SolicitudCompraForm, SolicitudCompraFormcrear, UserCreateForm, UserEditForm, UserCreateForm, DepartamentoForm, UsuarioDepartamentoForm, InstitucionForm
from .models import  FechaInsumo, Producto, Insumo, InsumoSolicitud, Perfil, Departamento, Seccion, SolicitudCompra, Subproducto, UsuarioDepartamento, Institucion, Servicio, ServicioSolicitud
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
from django.views.generic.detail import DetailView
from django.core.mail import BadHeaderError
from smtplib import SMTPException
from django.db.models import Count
from django.db.models.functions import ExtractYear, ExtractMonth
from datetime import date
from xhtml2pdf import pisa
from io import BytesIO
from django.contrib.auth.backends import ModelBackend
from django.db import connections


class TicketsAuthBackend(ModelBackend):
    """
    Backend que permite autenticar usuarios desde la base de datos de Tickets.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Conexión al alias 'tickets_db'
            with connections['tickets_db'].cursor() as cursor:
                user = User.objects.using('tickets_db').get(username=username)
                if user.check_password(password) and user.is_active:
                    return user
        except User.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.using('tickets_db').get(pk=user_id)
        except User.DoesNotExist:
            return None

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


from django.db import IntegrityError

from scompras_app.models_empleados import Empleado  # 🔹 modelo de empleados (Ticktes)

# ... imports iguales
from scompras_app.models_empleados import Empleado

@login_required
@grupo_requerido('Administrador', 'scompras')
def asignar_departamento_usuario(request):

    if request.method == 'POST':
        form = UsuarioDepartamentoForm(request.POST)
        if form.is_valid():
            UsuarioDepartamento.objects.create(
                usuario_id=form.cleaned_data['usuario'].id,   # ← solo el ID!
                departamento=form.cleaned_data['departamento'],
                seccion=form.cleaned_data['seccion']
            )
            messages.success(request, "Departamento asignado correctamente")
            return redirect("scompras:asignar_departamento")
        else:
            messages.error(request, "Corrige los errores del formulario.")
    else:
        form = UsuarioDepartamentoForm()

    # Asignaciones
    asignaciones = UsuarioDepartamento.objects.select_related('departamento', 'seccion')

    # Mapa empleados
    empleados_map = {
        e.user_id: e for e in Empleado.objects.using('tickets_db').all()
    }

    filas = []
    agrupado = {}

    for a in asignaciones:
        agrupado.setdefault(a.usuario_id, []).append(a)

    for uid, asigns in agrupado.items():
        user = User.objects.using('tickets_db').filter(id=uid).first()
        filas.append({
            'usuario': user,
            'empleado': empleados_map.get(uid),
            'asignaciones': asigns
        })

    return render(request, "scompras/asignar_departamento.html", {
        "form": form,
        "filas": filas
    })

    return render(request, 'scompras/asignar_departamento.html', context)




def eliminar_asignacion(request, usuario_id, departamento_id, seccion_id):
    """
    Elimina una asignación usuario-departamento-sección.
    """
    if request.method == 'POST':
        asignacion = get_object_or_404(
            UsuarioDepartamento,
            usuario_id=usuario_id,
            departamento_id=departamento_id,
            seccion_id=seccion_id
        )
        asignacion.delete()
        messages.success(request, 'Asignación eliminada correctamente.')
    else:
        messages.error(request, 'Método no permitido.')
    return redirect('scompras:asignar_departamento')


@login_required
@require_GET
def cargar_secciones(request):
    """
    Carga dinámica de secciones por departamento.
    """
    departamento_id = request.GET.get('departamento_id')
    secciones = Seccion.objects.filter(departamento_id=departamento_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse({'secciones': list(secciones)}, safe=False)

def ajax_cargar_secciones(request):
    departamento_id = request.GET.get('departamento_id')
    secciones = Seccion.objects.filter(departamento_id=departamento_id).values('id', 'nombre')
    secciones_list = list(secciones)
    return JsonResponse({'secciones': secciones_list})

@login_required
def lista_departamentos(request):
    user = request.user
    grupos_usuario = list(user.groups.values_list('name', flat=True))

    es_admin = 'Administrador' in grupos_usuario
    es_departamento = 'Departamento' in grupos_usuario
    es_scompras = 'scompras' in grupos_usuario

    if es_admin:
        # Admin ve todo y tiene acceso completo
        departamentos = Departamento.objects.all()
        departamentos_usuario_ids = list(departamentos.values_list('id', flat=True))
    elif es_departamento or es_scompras:
        # Solo departamentos asignados
        departamentos_usuario_ids = list(
            UsuarioDepartamento.objects.filter(usuario=user)
            .values_list('departamento_id', flat=True)
            .distinct()
        )
        departamentos = Departamento.objects.filter(id__in=departamentos_usuario_ids)
    else:
        # No tiene grupo válido
        departamentos_usuario_ids = []
        departamentos = Departamento.objects.none()

    return render(request, 'scompras/lista_departamentos.html', {
        'departamentos': departamentos,
        'departamentos_usuario_ids': departamentos_usuario_ids,
        'es_departamento': es_departamento,
        'es_admin': es_admin,
    })




@login_required
def detalle_seccion(request, departamento_id, seccion_id):
    seccion = get_object_or_404(Seccion, pk=seccion_id, departamento__id=departamento_id)
    user = request.user

    grupos_usuario = list(user.groups.values_list('name', flat=True))
    es_admin = 'Administrador' in grupos_usuario
    es_scompras = 'scompras' in grupos_usuario

    if not (es_admin or es_scompras):
        tiene_acceso = UsuarioDepartamento.objects.filter(
            usuario=user,
            departamento=seccion.departamento,
            seccion=seccion
        ).exists()
        if not tiene_acceso:
            return render(request, 'scompras/403.html', status=403)

    # Manejo del formulario
    if request.method == 'POST':
        form = SolicitudCompraFormcrear(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = user
            solicitud.departamento = seccion.departamento
            solicitud.seccion = seccion
            solicitud.save()
            messages.success(request, "Solicitud creada exitosamente.")
            return redirect('scompras:detalle_seccion', departamento_id=departamento_id, seccion_id=seccion_id)
        else:
            # Debug: errores en consola
            print(form.errors)
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = SolicitudCompraFormcrear()

    solicitudes = SolicitudCompra.objects.filter(seccion=seccion).order_by('-fecha_solicitud')[:10]
    secciones = seccion.departamento.secciones.filter(activo=True)
    todas_solicitudes = SolicitudCompra.objects.filter(seccion=seccion).order_by('-fecha_solicitud')


    context = {
        'seccion': seccion,
        'form': form,
        'solicitudes': solicitudes,
        'todas_solicitudes': todas_solicitudes, 
        'secciones': secciones,
    }
    return render(request, 'scompras/detalle_seccion.html', context)


@login_required
def detalle_seccion_usuario(request):
    user = request.user

    # Validar si pertenece al grupo "scompras"
    if not user.groups.filter(name='scompras').exists():
        return render(request, 'scompras/403.html', status=403)

    # Buscar la asignación del usuario a una sección
    asignacion = UsuarioDepartamento.objects.filter(usuario=user).select_related('departamento', 'seccion').first()
    
    if not asignacion or not asignacion.seccion:
        messages.warning(request, "No tienes asignada ninguna sección.")
        return render(request, 'scompras/sin_seccion.html')

    seccion = asignacion.seccion
    departamento = asignacion.departamento

    # Formulario para crear solicitudes
    if request.method == 'POST':
        form = SolicitudCompraFormcrear(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = user
            solicitud.departamento = departamento
            solicitud.seccion = seccion
            solicitud.save()
            messages.success(request, "Solicitud creada exitosamente.")
            return redirect('scompras:detalle_seccion_usuario')
        else:
            print(form.errors)
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = SolicitudCompraFormcrear()

    # Datos a mostrar
    solicitudes = SolicitudCompra.objects.filter(seccion=seccion).order_by('-fecha_solicitud')[:10]
    todas_solicitudes = SolicitudCompra.objects.filter(seccion=seccion).order_by('-fecha_solicitud')
    secciones = departamento.secciones.filter(activo=True)

    context = {
        'seccion': seccion,
        'departamento': departamento,
        'form': form,
        'solicitudes': solicitudes,
        'todas_solicitudes': todas_solicitudes,
        'secciones': secciones,
    }

    return render(request, 'scompras/detalle_seccion_usuario.html', context)


def ajax_cargar_subproductos(request):
    producto_id = request.GET.get('producto_id')
    print("Producto ID recibido en AJAX:", producto_id)
    if producto_id:
        subproductos = Subproducto.objects.filter(producto_id=producto_id).values('id', 'nombre')
        data = list(subproductos)
    else:
        data = []
    return JsonResponse(data, safe=False)


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


def crear_seccion(request, pk=None):
    if pk:
        seccion = get_object_or_404(Seccion, pk=pk)
        form = SeccionForm(request.POST or None, instance=seccion)
        mensaje_exito = "Sección actualizada correctamente."
    else:
        seccion = None
        form = SeccionForm(request.POST or None)
        mensaje_exito = "Sección creada correctamente."

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, mensaje_exito)
        return redirect('scompras:crear_seccion')

    secciones = Seccion.objects.select_related('departamento').all()

    context = {
        'form': form,
        'secciones': secciones,
    }
    return render(request, 'scompras/crear_seccion.html', context)

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

    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario editado correctamente.')
            return redirect('scompras:user_edit', user_id=user.id)
    else:
        form = UserEditForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'users': User.objects.all(),
    }
    return render(request, 'scompras/user_form_edit.html', context)

from django.utils.timezone import localtime
from django.template.defaultfilters import date as django_date

class SolicitudCompraDetailView(DetailView):
    model = SolicitudCompra
    template_name = 'scompras/detalle_solicitud.html'
    context_object_name = 'solicitud'


    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitud = self.get_object()

        # Convertir la fecha de solicitud a la zona horaria local
        solicitud.fecha_solicitud = localtime(solicitud.fecha_solicitud)

        # Formatear la fecha y agregarla al contexto
        context['fecha_solicitud_formateada'] = django_date(solicitud.fecha_solicitud, 'j \\d\\e F \\d\\e Y')

        context['insumos'] = Insumo.objects.all()
        context['detalles'] = InsumoSolicitud.objects.filter(solicitud=solicitud)
        context['servicios'] = ServicioSolicitud.objects.filter(solicitud=solicitud)
        context['ultima_fecha_insumo'] = FechaInsumo.objects.last()
        context['productos'] = Producto.objects.filter(activo=True)
        context['subproductos'] = Subproducto.objects.filter(activo=True)

        return context


from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.db.models import Count

@receiver(pre_save, sender=SolicitudCompra)
def generar_codigo_correlativo(sender, instance, **kwargs):
    # Asegurarse de que 'fecha_solicitud' esté definida antes de acceder al año
    if not instance.fecha_solicitud:
        return  # Si no hay fecha, no generar el código

    año = instance.fecha_solicitud.year

    # Obtener la abreviatura del departamento y sección
    dept_abrev = instance.seccion.departamento.abreviatura if instance.seccion else "GEN"
    secc_abrev = instance.seccion.abreviatura if instance.seccion else None

    # Contar solicitudes existentes en esa sección y año
    if instance.seccion:
        count = SolicitudCompra.objects.filter(
            seccion=instance.seccion,
            fecha_solicitud__year=año
        ).exclude(id=instance.id).count() + 1
    else:
        # Si no hay sección, contar solicitudes sin sección en ese año
        count = SolicitudCompra.objects.filter(
            seccion__isnull=True,
            usuario__usuario_departamento__departamento=instance.usuario.usuario_departamento_set.first().departamento,
            fecha_solicitud__year=año
        ).exclude(id=instance.id).count() + 1

    # Generar el código correlativo
    if secc_abrev and secc_abrev != dept_abrev:
        # Si la sección tiene una abreviatura diferente al departamento, incluir la abreviatura de la sección
        instance.codigo_correlativo = f'UPCV-{dept_abrev}-{secc_abrev}-{count:03d}-{año}'
    else:
        # Si la sección es igual al departamento o no existe sección, solo usar la abreviatura del departamento
        instance.codigo_correlativo = f'UPCV-{dept_abrev}-{count:03d}-{año}'


@require_POST
def eliminar_detalle_solicitud(request, detalle_id):
    """
    Elimina un InsumoSolicitud (detalle de insumo) de una solicitud de compra.
    """
    try:
        # Usamos InsumoSolicitud en lugar de DetalleSolicitud
        detalle = get_object_or_404(InsumoSolicitud, pk=detalle_id)
        
        # Lógica de eliminación
        detalle.delete()

        return JsonResponse({'success': True})
    
    # Asegúrate de atrapar la excepción correcta (InsumoSolicitud.DoesNotExist)
    except InsumoSolicitud.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'El insumo no existe.'}, status=404)
    
    except Exception as e:
        print("ERROR EN LA VISTA DE ELIMINACIÓN:", e) 
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@csrf_exempt
def eliminar_servicio_solicitud(request, servicio_id):
    if request.method == "POST":
        try:
            servicio = ServicioSolicitud.objects.get(id=servicio_id)
            servicio.delete()
            return JsonResponse({"success": True})
        except ServicioSolicitud.DoesNotExist:
            return JsonResponse({"success": False, "error": "Servicio no encontrado"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Método no permitido"})

from django.forms.models import model_to_dict

@require_POST
def agregar_insumo_solicitud(request):
    solicitud_id = request.POST.get('solicitud_id')
    codigo_presentacion = request.POST.get('codigo_presentacion', '').strip()
    cantidad = request.POST.get('cantidad')
    caracteristica = request.POST.get('caracteristica', '').strip()
    renglon = request.POST.get('renglon', '').strip()  # <-- Nuevo

    try:
        solicitud = SolicitudCompra.objects.get(id=solicitud_id)

        insumos = Insumo.objects.filter(codigo_presentacion__iexact=codigo_presentacion)
        if not insumos.exists():
            return JsonResponse({'success': False, 'error': 'Insumo no encontrado por código de presentación.'})

        insumo = insumos.first()

        if InsumoSolicitud.objects.filter(solicitud=solicitud, insumo=insumo).exists():
            return JsonResponse({'success': False, 'error': 'Este insumo ya está agregado.'})

        try:
            cantidad = int(cantidad)
            if cantidad <= 0:
                cantidad = 1
        except (TypeError, ValueError):
            cantidad = 1

        insumo_solicitud = InsumoSolicitud.objects.create(
            solicitud=solicitud,
            insumo=insumo,
            cantidad=cantidad,
            caracteristica_especial=caracteristica,
            renglon=renglon
        )

        detalle_id = insumo_solicitud.id 

        insumo_data = {
            'codigo_insumo': insumo.codigo_insumo,
            'nombre': insumo.nombre,
            'caracteristicas': insumo.caracteristicas or '-',
            'caracteristica_especial': caracteristica,
            'nombre_presentacion': insumo.nombre_presentacion,
            'cantidad_unidad_presentacion': insumo.cantidad_unidad_presentacion,
            'codigo_presentacion': insumo.codigo_presentacion,
            'cantidad': insumo_solicitud.cantidad,
            'renglon': insumo_solicitud.renglon,

        }

        return JsonResponse({'success': True, 'insumo': insumo_data, 'detalle_id': detalle_id})

    except SolicitudCompra.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitud no encontrada.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



def detalle_solicitud(request, solicitud_id):
    solicitud = SolicitudCompra.objects.get(id=solicitud_id)
    detalles = InsumoSolicitud.objects.filter(solicitud=solicitud)
    servicios = ServicioSolicitud.objects.filter(solicitud=solicitud)  # 👈 ESTA LÍNEA ES CLAVE
    productos = Producto.objects.filter(activo=True)
    subproductos = Subproducto.objects.filter(activo=True)

    return render(request, 'scompras/detalle_solicitud.html', {
        'solicitud': solicitud,
        'detalles': detalles,
        'productos': productos,
        'subproductos': subproductos,
        'servicios': servicios,
    })

def obtener_subproductos(request, producto_id):
    subproductos = Subproducto.objects.filter(producto_id=producto_id, activo=True)
    data = [{'id': s.id, 'nombre': s.nombre} for s in subproductos]
    return JsonResponse({'subproductos': data})


@require_POST
def editar_solicitud(request):
    try:
        solicitud = SolicitudCompra.objects.get(id=request.POST.get('solicitud_id'))
    except SolicitudCompra.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Solicitud no encontrada.'})

    form = SolicitudCompraForm(request.POST, instance=solicitud)

    if form.is_valid():
        form.save()
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'errors': form.errors})

@login_required
@csrf_exempt
def finalizar_solicitud(request):
    if request.method == "POST":
        try:
            # Cargar los datos JSON del cuerpo de la solicitud
            data = json.loads(request.body)
            solicitud_id = data.get("solicitud_id")

            if not solicitud_id:
                return JsonResponse({"success": False, "error": "ID de solicitud no proporcionado"})

            # Obtener la solicitud con el ID proporcionado, si no existe, devolver un error 404
            solicitud = get_object_or_404(SolicitudCompra, id=solicitud_id)

            # Verificar si la solicitud tiene un estado válido para ser finalizada
            if solicitud.estado not in ['Creada', 'Rechazada']:
                return JsonResponse({"success": False, "error": f"Estado de la solicitud debe ser 'Creada' o 'Rechazada' para poder finalizarla."})

            # Actualizar el estado a "Finalizada"
            solicitud.estado = "Finalizada"
            # Guardar solo el campo 'estado' sin afectar otros campos como el 'codigo_correlativo'
            solicitud.save(update_fields=['estado'])

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"})


@login_required
@csrf_exempt
def rechazar_solicitud(request):
    if request.method == "POST":
        try:
            # Cargar los datos JSON del cuerpo de la solicitud
            data = json.loads(request.body)
            solicitud_id = data.get("solicitud_id")

            if not solicitud_id:
                return JsonResponse({"success": False, "error": "ID de solicitud no proporcionado"})

            # Obtener la solicitud con el ID proporcionado, si no existe, devolver un error 404
            solicitud = get_object_or_404(SolicitudCompra, id=solicitud_id)

            # Verificar si la solicitud tiene un estado válido para ser rechazada
            if solicitud.estado not in ['Creada', 'Finalizada']:
                return JsonResponse({"success": False, "error": f"Estado de la solicitud debe ser 'Creada' o 'Finalizada' para poder rechazarla."})

            # Actualizar el estado a "Rechazada"
            solicitud.estado = "Rechazada"
            # Guardar solo el campo 'estado' sin afectar otros campos como el 'codigo_correlativo'
            solicitud.save(update_fields=['estado'])

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"})



def generar_pdf_solicitud(request, solicitud_id):
    # Obtener la solicitud desde la base de datos
    solicitud = SolicitudCompra.objects.get(id=solicitud_id)

    # Obtener los detalles de los insumos asociados a la solicitud
    detalles = InsumoSolicitud.objects.filter(solicitud=solicitud)

    # Obtener todos los insumos si es necesario
    insumos = Insumo.objects.all()

    # Crear el contexto para pasar al template
    context = {
        'solicitud': solicitud,
        'detalles': detalles,
        'insumos': insumos,
        
    }

    # Renderizar el template a HTML con el contexto
    html = render_to_string('scompras/solicitud_pdf.html', context)

    # Crear un buffer de memoria para generar el PDF
    buffer = BytesIO()

    # Convertir el HTML a PDF usando xhtml2pdf
    pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), buffer)

    if pdf.err:
        return HttpResponse("Error al generar el PDF", status=500)

    # Generar la respuesta HTTP para abrir el PDF en una nueva ventana
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="solicitud.pdf"'  # Cambiar 'attachment' por 'inline'
    response.write(buffer.getvalue())

    return response

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


def dahsboard(request):
    # Agrupar solicitudes por sección y año
    solicitudes_por_anio = (
        SolicitudCompra.objects
        .annotate(anio=ExtractYear('fecha_solicitud'))
        .values('seccion__nombre', 'anio')  # Agrupar por nombre de sección
        .annotate(total=Count('id'))  # Cuenta las solicitudes por cada sección y año
        .order_by('anio', 'seccion__nombre')
    )

    # Agrupar solicitudes por sección y mes (del año actual)
    anio_actual = date.today().year

    solicitudes_por_mes = (
        SolicitudCompra.objects
        .filter(fecha_solicitud__year=anio_actual)
        .annotate(mes=ExtractMonth('fecha_solicitud'))
        .values('seccion__nombre', 'mes')  # Agrupar por nombre de sección
        .annotate(total=Count('id'))
        .order_by('mes', 'seccion__nombre')
    )

    # Obtener la lista de años disponibles en las solicitudes
    anios_disponibles = SolicitudCompra.objects.annotate(anio=ExtractYear('fecha_solicitud')).values('anio').distinct().order_by('anio')
    anios_list = [anio['anio'] for anio in anios_disponibles]

    context = {
        'solicitudes_por_anio': list(solicitudes_por_anio),
        'solicitudes_por_mes': list(solicitudes_por_mes),
        'anio_actual': anio_actual,
        'anios': anios_list,  # Pasamos la lista de años disponibles
    }

    return render(request, 'scompras/dahsboard.html', context)


from django.db.models import Count
from django.db.models.functions import ExtractYear, ExtractMonth
from datetime import date

@login_required
def dashboard_usuario(request):
    user = request.user

    asignacion = (
        UsuarioDepartamento.objects
        .filter(usuario=user)
        .select_related('seccion', 'departamento')
        .first()
    )

    if not asignacion or not asignacion.seccion:
        return render(request, 'scompras/sin_seccion.html', {
            'mensaje': 'No tienes asignada ninguna sección.'
        })

    seccion = asignacion.seccion

    # 🔹 Agrupar solicitudes por año y mes (una sola consulta)
    solicitudes_por_anio_mes = (
        SolicitudCompra.objects
        .filter(seccion=seccion)
        .annotate(
            anio=ExtractYear('fecha_solicitud'),
            mes=ExtractMonth('fecha_solicitud')
        )
        .values('anio', 'mes')
        .annotate(total=Count('id'))
        .order_by('anio', 'mes')
    )

    # 🔹 Años disponibles (por si quieres filtros o mostrar en el dashboard)
    anios_disponibles = (
        SolicitudCompra.objects
        .filter(seccion=seccion)
        .annotate(anio=ExtractYear('fecha_solicitud'))
        .values('anio')
        .distinct()
        .order_by('anio')
    )
    anios_list = [a['anio'] for a in anios_disponibles]

    context = {
        'seccion': seccion,
        'departamento': asignacion.departamento,
        'solicitudes_por_anio_mes': list(solicitudes_por_anio_mes),
        'anios': anios_list,
    }

    return render(request, 'scompras/dashboard_usuario.html', context)



def acceso_denegado(request, exception=None):
    return render(request, 'scompras/403.html', status=403)

@login_required
def detalle_departamento(request, pk):
    departamento = get_object_or_404(Departamento, pk=pk)
    user = request.user

    # Verificar si es administrador
    es_admin = user.groups.filter(name='Administrador').exists()

    # Si NO es admin, verificar si tiene asignado el departamento
    if not es_admin and not UsuarioDepartamento.objects.filter(usuario=user, departamento=departamento).exists():
        return render(request, 'scompras/403.html', status=403)

    # Obtener todas las secciones del departamento
    secciones_departamento = Seccion.objects.filter(departamento=departamento)

    # Si es admin, tiene acceso a todas las secciones
    if es_admin:
        secciones_usuario_ids = list(secciones_departamento.values_list('id', flat=True))
    else:
        # Filtrar secciones según permisos
        secciones_usuario_ids = UsuarioDepartamento.objects.filter(
            usuario=user,
            departamento=departamento
        ).values_list('seccion_id', flat=True)

    if request.method == 'POST':
        form = SolicitudCompraForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = user

            # Validar acceso a la sección
            if solicitud.seccion.id not in secciones_usuario_ids:
                return render(request, 'scompras/403.html', status=403)

            solicitud.departamento = departamento
            solicitud.save()
            return redirect('scompras:detalle_departamento', pk=departamento.pk)
    else:
        form = SolicitudCompraForm()

    solicitudes = SolicitudCompra.objects.filter(
        seccion__departamento=departamento
    ).order_by('-fecha_solicitud')

    return render(request, 'scompras/detalle_departamento.html', {
        'departamento': departamento,
        'secciones': secciones_departamento,
        'secciones_usuario_ids': list(secciones_usuario_ids),
        'form': form,
        'solicitudes': solicitudes,
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
                    return redirect('scompras:dashboard_usuario')
            # Si no se encuentra el grupo adecuado, se redirige a una página por defecto
            return redirect('scompras:signin')
        else:
            # Si el formulario no es válido, se retorna con el error
            return render(request, 'scompras/login.html', {
                'form': form,  # Pasamos el formulario con los errores
                'error': 'Usuario o contraseña incorrectos',
                'institucion': institucion,
            })





def descargar_insumos_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Insumos"

    # Escribir encabezados
    encabezados = [
        'Renglón', 'Código de Insumo', 'Nombre', 'Características',
        'Nombre de Presentación', 'Cantidad y Unidad de Medida de Presentación',
        'Código de Presentación'
    ]
    ws.append(encabezados)

    # Escribir datos
    for insumo in Insumo.objects.all():
        ws.append([
            insumo.renglon,
            insumo.codigo_insumo,
            insumo.nombre,
            insumo.caracteristicas,
            insumo.nombre_presentacion,
            insumo.cantidad_unidad_presentacion,
            insumo.codigo_presentacion,

        ])

    # Preparar la respuesta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename=insumos.xlsx'
    wb.save(response)
    return response

def insumos_disponibles_json(request):
    """
    Retorna la lista completa de insumos disponibles en formato JSON.
    Ideal para cargar una tabla simple o un DataTables sin server-side processing
    si la cantidad de datos es manejable (cientos o pocos miles).
    """
    insumos_queryset = Insumo.objects.all().order_by('nombre')
    
    data = []
    for insumo in insumos_queryset:
        data.append({
            'codigo_insumo': insumo.codigo_insumo,
            'nombre': insumo.nombre,
            'caracteristicas': insumo.caracteristicas if insumo.caracteristicas else '-',
            'nombre_presentacion': insumo.nombre_presentacion,
            'cantidad_unidad_presentacion': insumo.cantidad_unidad_presentacion,
            'codigo_presentacion': insumo.codigo_presentacion,
        })

    return JsonResponse({'data': data})

@csrf_exempt
def agregar_servicio_solicitud(request):
    if request.method == "POST":
        try:
            solicitud_id = request.POST.get("solicitud_id")
            cantidad = int(request.POST.get("cantidad"))
            concepto = request.POST.get("concepto")
            renglon = request.POST.get("renglon")
            unidad_medida = request.POST.get("unidad_medida")
            caracteristica_especial = request.POST.get("caracteristica_especial", "").strip()

            solicitud = SolicitudCompra.objects.get(id=solicitud_id)

            # Crear el servicio con todos los campos
            servicio = Servicio.objects.create(
                concepto=concepto.strip(),
                renglon=renglon.strip(),
                caracteristica_especial=caracteristica_especial or None,
                unidad_medida=unidad_medida.strip(),
            )

            ServicioSolicitud.objects.create(
                solicitud=solicitud,
                servicio=servicio,
                cantidad=cantidad,
            )

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"})



@csrf_exempt
def insumos_json(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    # 🔍 Filtros personalizados que vienen del frontend
    renglon = request.GET.get('renglon', '').strip()
    codigo_insumo = request.GET.get('codigo_insumo', '').strip()
    codigo_presentacion = request.GET.get('codigo_presentacion', '').strip()

    queryset = Insumo.objects.all()

    # 🔹 Filtros personalizados individuales
    if renglon:
        queryset = queryset.filter(renglon__icontains=renglon)
    if codigo_insumo:
        queryset = queryset.filter(codigo_insumo__icontains=codigo_insumo)
    if codigo_presentacion:
        queryset = queryset.filter(codigo_presentacion__icontains=codigo_presentacion)

    # 🔹 Búsqueda global de DataTables
    if search_value:
        queryset = queryset.filter(
            Q(renglon__icontains=search_value) |
            Q(codigo_insumo__icontains=search_value) |
            Q(nombre__icontains=search_value) |
            Q(caracteristicas__icontains=search_value) |
            Q(nombre_presentacion__icontains=search_value) |
            Q(cantidad_unidad_presentacion__icontains=search_value) |
            Q(codigo_presentacion__icontains=search_value)
        )

    total_count = Insumo.objects.count()
    filtered_count = queryset.count()
    queryset = queryset[start:start + length]

    data = [
        [
            insumo.renglon,
            insumo.codigo_insumo,
            insumo.nombre,
            insumo.caracteristicas,
            insumo.nombre_presentacion,
            insumo.cantidad_unidad_presentacion,
            insumo.codigo_presentacion
        ]
        for insumo in queryset
    ]

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total_count,
        'recordsFiltered': filtered_count,
        'data': data
    })

def importar_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        fecha_form = FechaInsumoForm(request.POST)  # Formulario para la fecha

        if form.is_valid() and fecha_form.is_valid():  # Validar ambos formularios
            archivo = request.FILES['archivo_excel']
            df = pd.read_excel(archivo)

            # Eliminar los datos anteriores
            Insumo.objects.all().delete()

            # Crear una lista para guardar los objetos que se crearán
            nuevos_insumos = []

            for _, row in df.iterrows():
                insumo = Insumo(
                    renglon=row['RENGLÓN'],
                    codigo_insumo=row['CÓDIGO DE INSUMO'],
                    nombre=row['NOMBRE'],
                    caracteristicas=row['CARACTERÍSTICAS'],
                    nombre_presentacion=row['NOMBRE DE LA PRESENTACIÓN'],
                    cantidad_unidad_presentacion=row['CANTIDAD Y UNIDAD DE MEDIDA DE LA PRESENTACIÓN'],
                    codigo_presentacion=row['CÓDIGO DE PRESENTACIÓN'],
                    fecha_actualizacion=timezone.now()
                )
                nuevos_insumos.append(insumo)

            # Guardar todos los nuevos insumos de una vez
            Insumo.objects.bulk_create(nuevos_insumos)

            # Aquí es donde se captura la fecha del formulario de fecha
            fecha_in = fecha_form.save(commit=False)
            # La fecha capturada será la fecha proporcionada por el formulario (no la actual)
            fecha_in.fechainsumo = fecha_form.cleaned_data['fechainsumo']
            fecha_in.save()

            # Redirigir con un parámetro de sesión para pasar los últimos insumos
            request.session['importados'] = True
            return redirect('scompras:catalogo_insumos_view')
    else:
        form = ExcelUploadForm()
        fecha_form = FechaInsumoForm()  # Iniciar el formulario de fecha

    return render(request, 'scompras/importar_excel.html', {'form': form, 'fecha_form': fecha_form})



def catalogo_insumos_view(request):
    # Obtener los insumos
    insumos = Insumo.objects.all().order_by('-fecha_actualizacion')
    
    # Obtener la última fecha de insumo (último registro de fechainsumo)
    ultima_fecha_insumo = FechaInsumo.objects.last()  # Obtiene el último registro de la tabla fechainsumo
    
    return render(request, 'scompras/confirmacion.html', {
        'insumos': insumos,
        'ultima_fecha_insumo': ultima_fecha_insumo
    })