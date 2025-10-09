from django import forms
from django.contrib.auth.models import User, Group
from django.forms import CheckboxInput, DateInput, inlineformset_factory, modelformset_factory
from django.core.exceptions import ValidationError


from .models import FechaInsumo, Insumo, Perfil, Departamento, Seccion, SolicitudCompra, UsuarioDepartamento, Institucion

from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce



from django import forms
from .models import Institucion

from django.core.exceptions import ValidationError

class InstitucionForm(forms.ModelForm):
    pagina_web = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Ingrese URL que comience con www., sin http/https.'
    )

    class Meta:
        model = Institucion
        fields = ['nombre', 'direccion', 'telefono', 'pagina_web', 'logo', 'logo2']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            # 'pagina_web': forms.URLInput(attrs={'class': 'form-control'}),  # quitamos este
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'logo2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_pagina_web(self):
        url = self.cleaned_data.get('pagina_web')
        if url:
            if not url.startswith('www.'):
                raise ValidationError('La URL debe comenzar con "www."')
            # Añadimos http:// para que sea una URL válida
            url = 'http://' + url
        return url



class UserCreateForm(forms.ModelForm):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label="Contraseña"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label="Confirmar Contraseña"
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    foto = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')

        if password != confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data
    
class UserEditForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Grupo",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        if self.instance and self.instance.pk:
            groups = self.instance.groups.all()
            if groups.exists():
                self.fields['group'].initial = groups.first()



class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['id_departamento', 'nombre', 'descripcion']
        widgets = {
            'id_departamento': forms.TextInput(attrs={'placeholder': 'ID del departamento', 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre del departamento', 'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'placeholder': 'Descripción del departamento', 'rows': 4, 'cols': 40, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(DepartamentoForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'


class UserForm(forms.ModelForm):
    new_password = forms.CharField(
        required=True, 
        widget=forms.PasswordInput, 
        label="Contraseña"
    )
    confirm_password = forms.CharField(
        required=True, 
        widget=forms.PasswordInput, 
        label="Confirmar Contraseña"
    )
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=True, label="Grupo")
    foto = forms.ImageField(required=False, label="Foto de perfil")  # Agregamos el campo aquí

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

        # Mostrar foto existente si está editando
        if self.instance.pk:
            try:
                self.fields['foto'].initial = self.instance.perfil.foto
            except Perfil.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Las contraseñas no coinciden.")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])

        if commit:
            user.save()
            user.groups.set([self.cleaned_data['group']])
            # Guardar o crear perfil
            foto = self.cleaned_data.get('foto')
            perfil, created = Perfil.objects.get_or_create(user=user)
            if foto:
                perfil.foto = foto
                perfil.save()

        return user
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        
        
        # Agregar la clase 'form-control' a todos los campos del formulario
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'
            
class UsuarioDepartamentoForm(forms.ModelForm):
    departamento = forms.ModelChoiceField(queryset=Departamento.objects.all(), required=True)
    seccion = forms.ModelChoiceField(queryset=Seccion.objects.none(), required=False)

    class Meta:
        model = UsuarioDepartamento
        fields = ['usuario', 'departamento', 'seccion']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Añadir la clase form-control a todos los campos
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

        # Cargar queryset para secciones según departamento
        if 'departamento' in self.data:
            try:
                departamento_id = int(self.data.get('departamento'))
                self.fields['seccion'].queryset = Seccion.objects.filter(departamento_id=departamento_id).order_by('nombre')
            except (ValueError, TypeError):
                self.fields['seccion'].queryset = Seccion.objects.none()
        elif self.instance.pk and self.instance.departamento:
            self.fields['seccion'].queryset = Seccion.objects.filter(departamento=self.instance.departamento).order_by('nombre')
        else:
            self.fields['seccion'].queryset = Seccion.objects.none()

        
class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['foto']
        widgets = {
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
  


class SolicitudCompraForm(forms.ModelForm):
    class Meta:
        model = SolicitudCompra
        fields = ['descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe la solicitud',
            }),
        }



class ExcelUploadForm(forms.Form):
    archivo_excel = forms.FileField()

    def __init__(self, *args, **kwargs):
        super(ExcelUploadForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            # Si es tipo FileField, normalmente se usa 'form-control' o 'form-control-file'
            css_class = 'form-control'
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + f' {css_class}'

class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['renglon', 'codigo_insumo', 'nombre', 'caracteristicas', 
                  'nombre_presentacion', 'cantidad_unidad_presentacion', 
                  'codigo_presentacion', 'fecha_actualizacion']
        widgets = {
            'fecha_actualizacion': forms.DateTimeInput(attrs={'type': 'datetime-local'})  # Usamos el widget para una entrada de fecha y hora
        }

class FechaInsumoForm(forms.ModelForm):
    class Meta:
        model = FechaInsumo
        fields = ['fechainsumo']
        widgets = {
            'fechainsumo': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(FechaInsumoForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'