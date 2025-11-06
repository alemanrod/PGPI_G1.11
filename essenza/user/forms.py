# user/forms.py (Crea este archivo)
from django import forms
from .models import Usuario # Importa tu modelo User personalizado

class RegisterForm(forms.ModelForm):
    """
    Formulario de registro personalizado basado en el mockup.
    """
    class Meta:
        model = Usuario
        
        # Campos que se pedirán en el formulario
        fields = [
            'name',  # Corresponde a 'Nombre'
            'email',       # Corresponde a 'Correo electrónico'
            'foto',        # El nuevo campo 'Foto'
            'password',   # Contraseña
        ]
        
        # Etiquetas para que coincidan 100% con el mockup
        labels = {
            'name': 'Nombre',
            'email': 'Correo electrónico',
            'foto': 'Foto',
            'password': 'Contraseña',
        }

    def _init_(self, *args, **kwargs):
        super(RegisterForm, self)._init_(*args, **kwargs)
        
        # Hacemos que 'Nombre', 'Email' y 'Contraseña' sean obligatorios
        self.fields['name'].required = True
        self.fields['email'].required = True
        self.fields['foto'].required = False  # 'Foto' es opcional
        self.fields['password'].required = True