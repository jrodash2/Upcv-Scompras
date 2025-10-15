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
import openpyxl
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
from .form import ExcelUploadForm, FechaInsumoForm, PerfilForm, SolicitudCompraForm, UserCreateForm, UserEditForm, UserCreateForm, DepartamentoForm, UsuarioDepartamentoForm, InstitucionForm
from .models import  FechaInsumo, Insumo, InsumoSolicitud, Perfil, Departamento, Seccion, SolicitudCompra, Subproducto, UsuarioDepartamento, Institucion
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
            except IntegrityError:
                messages.error(request, 'Esta asignación usuario-departamento-sección ya existe.')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = UsuarioDepartamentoForm()

    asignaciones = UsuarioDepartamento.objects.select_related('usuario', 'departamento', 'seccion')
    usuarios_con_departamentos = defaultdict(list)
    for asignacion in asignaciones:
        usuarios_con_departamentos[asignacion.usuario].append({
            'departamento': asignacion.departamento,
            'seccion': asignacion.seccion,
        })

    context = {
        'form': form,
        'usuarios_con_departamentos': usuarios_con_departamentos.items(),
    }
    return render(request, 'scompras/asignar_departamento.html', context)


def eliminar_asignacion(request, usuario_id, departamento_id, seccion_id):
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
    departamento_id = request.GET.get('departamento_id')
    secciones = Seccion.objects.filter(departamento_id=departamento_id).values('id', 'nombre').order_by('nombre')
    return JsonResponse(list(secciones), safe=False)

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

    # Obtener los nombres de los grupos del usuario
    grupos_usuario = list(user.groups.values_list('name', flat=True))

    es_admin = 'Administrador' in grupos_usuario
    es_scompras = 'scompras' in grupos_usuario

    # Si no es admin ni scompras, verificar si está asignado al departamento y sección
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
        form = SolicitudCompraForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.usuario = user
            solicitud.departamento = seccion.departamento
            solicitud.seccion = seccion
            solicitud.save()
            messages.success(request, "Solicitud creada exitosamente.")
            return redirect('scompras:detalle_seccion', departamento_id=departamento_id, seccion_id=seccion_id)
    else:
        form = SolicitudCompraForm()

    solicitudes = SolicitudCompra.objects.filter(seccion=seccion).order_by('-fecha_solicitud')[:10]
    secciones = seccion.departamento.secciones.filter(activo=True)

    context = {
        'seccion': seccion,
        'form': form,
        'solicitudes': solicitudes,
        'secciones': secciones,
    }

    return render(request, 'scompras/detalle_seccion.html', context)



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



class SolicitudCompraDetailView(DetailView):
    model = SolicitudCompra
    template_name = 'scompras/detalle_solicitud.html'
    context_object_name = 'solicitud'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitud = self.get_object()

        context['insumos'] = Insumo.objects.all()  # Para el formulario, si es necesario
        context['detalles'] = InsumoSolicitud.objects.filter(solicitud=solicitud)
        context['ultima_fecha_insumo'] = FechaInsumo.objects.last()

        return context

@csrf_exempt
def agregar_insumo_solicitud(request):
    if request.method == 'POST':
        solicitud_id = request.POST.get('solicitud_id')
        insumo_codigo = request.POST.get('insumo_codigo')

        # Intentar obtener un solo insumo con filter().first()
        insumo = Insumo.objects.filter(codigo_insumo=insumo_codigo).first()
        if not insumo:
            return JsonResponse({'success': False, 'error': 'Insumo no encontrado.'})

        # Aquí agregar lógica para asociar el insumo a la solicitud
        # Ejemplo:
        # solicitud = Solicitud.objects.get(id=solicitud_id)
        # solicitud.insumos.add(insumo)
        # solicitud.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Método no permitido'})


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


@csrf_exempt  # Si estás teniendo problemas con CSRF en peticiones Ajax, puedes usar esto temporalmente
def insumos_json(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '').strip()

    queryset = Insumo.objects.all()

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

    data = []
    for insumo in queryset:
        data.append([
            insumo.renglon,
            insumo.codigo_insumo,
            insumo.nombre,
            insumo.caracteristicas,
            insumo.nombre_presentacion,
            insumo.cantidad_unidad_presentacion,
            insumo.codigo_presentacion
        ])

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