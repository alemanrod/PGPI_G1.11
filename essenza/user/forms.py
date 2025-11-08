# user/forms.py
from django import forms

class LoginForm(forms.Form):
    email = forms.CharField(
        label="Correo electrónico o usuario",
        widget=forms.TextInput(attrs={"placeholder": "Introduce tu correo electrónico"})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Introduce tu contraseña"})
    )
