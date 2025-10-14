from django import forms
from django.contrib.auth.models import User, Group
from django.forms import CheckboxInput, DateInput, inlineformset_factory, modelformset_factory
from django.core.exceptions import ValidationError


from .models import FechaInsumo, Insumo, Perfil, Departamento, Seccion, SolicitudCompra, Subproducto, UsuarioDepartamento, Institucion

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



from django import forms
from django.contrib.auth.models import User, Group
from .models import Perfil

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
    cargo = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
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

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('new_password')
        user.set_password(password)

        if commit:
            user.save()
            # Asignar grupo
            group = self.cleaned_data.get('group')
            if group:
                user.groups.set([group])

            # Crear perfil
            cargo = self.cleaned_data.get('cargo')
            foto = self.cleaned_data.get('foto')
            Perfil.objects.update_or_create(
                user=user,
                defaults={'cargo': cargo, 'foto': foto}
            )

        return user

class UserEditForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Grupo",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cargo = forms.CharField(
        max_length=100,
        required=False,
        label="Cargo",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    foto = forms.ImageField(
        required=False,
        label="Foto de perfil",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
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

        # Cargar valores iniciales del perfil (cargo y foto)
        if self.instance and self.instance.pk:
            perfil = getattr(self.instance, 'perfil', None)
            if perfil:
                self.fields['cargo'].initial = perfil.cargo
                self.fields['foto'].initial = perfil.foto

            groups = self.instance.groups.all()
            if groups.exists():
                self.fields['group'].initial = groups.first()

    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            # Actualizar grupo
            group = self.cleaned_data.get('group')
            if group:
                user.groups.set([group])
            else:
                user.groups.clear()

            # Actualizar perfil
            perfil, created = Perfil.objects.get_or_create(user=user)
            perfil.cargo = self.cleaned_data.get('cargo')
            foto = self.cleaned_data.get('foto')

            if foto:
                perfil.foto = foto

            perfil.save()

        return user



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
    foto = forms.ImageField(required=False, label="Foto de perfil")
    cargo = forms.CharField(required=False, label="Cargo", widget=forms.TextInput(attrs={'class': 'form-control'}))  # nuevo campo cargo

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

        # Mostrar foto y cargo existentes si está editando
        if self.instance.pk:
            try:
                self.fields['foto'].initial = self.instance.perfil.foto
                self.fields['cargo'].initial = self.instance.perfil.cargo  # inicializamos cargo
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
            cargo = self.cleaned_data.get('cargo')  # obtener valor cargo
            perfil, created = Perfil.objects.get_or_create(user=user)
            if foto:
                perfil.foto = foto
            perfil.cargo = cargo  # guardamos cargo
            perfil.save()

        return user

            
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
        fields = ['descripcion', 'producto', 'subproducto']
        widgets = {
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'producto': forms.Select(attrs={'class': 'form-control', 'id': 'id_producto'}),
            'subproducto': forms.Select(attrs={'class': 'form-control', 'id': 'id_subproducto'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subproducto'].queryset = Subproducto.objects.none()

        # Primero, si viene producto en data (POST o GET)
        if 'producto' in self.data:
            try:
                producto_id = int(self.data.get('producto'))
                self.fields['subproducto'].queryset = Subproducto.objects.filter(producto_id=producto_id)
            except (ValueError, TypeError):
                pass
        # Segundo, si la instancia ya tiene producto relacionado (edición)
        elif self.instance.pk and self.instance.producto:
            self.fields['subproducto'].queryset = self.instance.producto.subproductos.all()
        # Tercero, si en initial o kwargs se pasa un producto, cargar también subproductos
        elif 'initial' in kwargs and 'producto' in kwargs['initial']:
            try:
                producto_id = int(kwargs['initial']['producto'])
                self.fields['subproducto'].queryset = Subproducto.objects.filter(producto_id=producto_id)
            except (ValueError, TypeError):
                pass



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