from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


app_name = 'scompras'

# Manejador global de errores (esto debe estar fuera de urlpatterns)
handler403 = 'scompras_app.views.acceso_denegado'  # Asegúrate que el nombre de tu app sea correcto

urlpatterns = [
    path('', views.home, name='home'), 
    path('dahsboard/', views.dahsboard, name='dahsboard'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),

    # Acceso denegado
    path('no-autorizado/', views.acceso_denegado, name='acceso_denegado'),
    path('importar-excel/', views.importar_excel, name='importar_excel'),
    path('catalogo-insumos/', views.catalogo_insumos_view, name='catalogo_insumos_view'),  
    path('insumos-json/', views.insumos_json, name='insumos_json'),
    path('descargar-insumos/', views.descargar_insumos_excel, name='descargar_insumos'),
    # Usuarios
    path('usuario/crear/', views.user_create, name='user_create'),
    path('usuario/editar/<int:user_id>/', views.user_edit, name='user_edit'),

    path('usuario/eliminar/<int:user_id>/', views.user_delete, name='user_delete'),

    # Departamentos
    path('departamento/', views.crear_departamento, name='crear_departamento'),
    path('departamento/editar/<int:pk>/', views.editar_departamento, name='editar_departamento'),
    path('departamentos/', views.lista_departamentos, name='lista_departamentos'),
    path('departamento/<int:pk>/', views.detalle_departamento, name='detalle_departamento'),
    path('departamento/<int:departamento_id>/seccion/<int:seccion_id>/', views.detalle_seccion, name='detalle_seccion'),
    path('seccion/<int:pk>/', views.detalle_seccion, name='detalle_seccion'), 
    path('ajax/cargar-secciones/', views.ajax_cargar_secciones, name='ajax_cargar_secciones'),
    


    # Asignación de usuarios a departamentos
    path('asignar-usuario-departamento/', views.asignar_departamento_usuario, name='asignar_departamento'),
    path('eliminar-asignacion/<int:usuario_id>/<int:departamento_id>/<int:seccion_id>/', views.eliminar_asignacion, name='eliminar_asignacion'),
    path('editar_institucion/', views.editar_institucion, name='editar_institucion'),
    # Cambiar contraseña
    path('cambiar-contraseña/', auth_views.PasswordChangeView.as_view(
        template_name='scompras/password_change_form.html',
        success_url='/cambiar-contraseña/hecho/'  # Redirección tras éxito
    ), name='password_change'),

    path('cambiar-contraseña/hecho/', auth_views.PasswordChangeDoneView.as_view(
        template_name='scompras/password_change_done.html'
    ), name='password_change_done'),
    
  


]
