from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario 

class LoginForm(forms.Form):
    email = forms.CharField(
        label="Correo electrónico o usuario",
        widget=forms.TextInput(attrs={"placeholder": "Introduce tu correo electrónico"})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Introduce tu contraseña"})
    )

class RegisterForm(UserCreationForm):
    
    first_name = forms.CharField(
        label="Nombre", 
        required=True
    )
    last_name = forms.CharField(
        label="Apellidos", 
        required=True
    )
    email = forms.EmailField(
        label="Correo electrónico", 
        required=True
    )
    foto = forms.ImageField(
        label="Foto (Opcional)", 
        required=False
    )

    class Meta(UserCreationForm.Meta):
        
        model = Usuario

        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'foto')
