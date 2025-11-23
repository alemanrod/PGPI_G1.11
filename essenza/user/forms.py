from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Role, Usuario


class LoginForm(forms.Form):
    email = forms.CharField(
        label="Correo electrónico o usuario",
        widget=forms.TextInput(
            attrs={"placeholder": "Introduce tu correo electrónico"}
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Introduce tu contraseña"}),
    )


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre", required=True)
    last_name = forms.CharField(label="Apellidos", required=True)
    email = forms.EmailField(label="Correo electrónico", required=True)
    photo = forms.ImageField(label="Foto (Opcional)", required=False)

    class Meta(UserCreationForm.Meta):
        model = Usuario

        fields = ("first_name", "last_name", "email", "photo")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", required=True)
    last_name = forms.CharField(label="Apellidos", required=True)
    email = forms.EmailField(label="Correo electrónico", required=True)
    photo = forms.ImageField(
        label="Foto (Opcional)", required=False, widget=forms.FileInput
    )
    remove_photo = forms.BooleanField(
        required=False, label="Eliminar foto de perfil actual"
    )

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "photo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["email"].disabled = True
        self.fields["email"].help_text = "El correo electrónico no se puede modificar."

        # Ocultar checkbox si no hay foto
        if not self.instance or not self.instance.photo:
            self.fields["remove_photo"].widget = forms.HiddenInput()

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data.get("remove_photo") and not self.files.get("photo"):
            try:
                if user.photo:
                    user.photo.delete(save=False)
            except Exception:
                pass
            user.photo = None

        if commit:
            user.save()
        return user


class UserCreationFormAdmin(RegisterForm):
    # Añadimos SOLO lo que le falta al registro normal: Control de Rol y Estado
    role = forms.ChoiceField(
        choices=Role.choices,
        label="Rol Inicial",
        required=True,
        initial=Role.USER,  # Por defecto creamos clientes
    )

    is_active = forms.BooleanField(
        label="Cuenta Activa",
        required=False,
        initial=True,
        help_text="Desmarca si quieres crearlo pero bloquearle el acceso.",
    )

    class Meta(RegisterForm.Meta):
        # Heredamos el modelo de RegisterForm
        model = Usuario
        # Añadimos los nuevos campos a los que ya tenía RegisterForm
        fields = RegisterForm.Meta.fields + ("role", "is_active")


class UserEditFormAdmin(forms.ModelForm):
    first_name = forms.CharField(label="Nombre", required=False)
    last_name = forms.CharField(label="Apellidos", required=False)
    email = forms.EmailField(label="Correo electrónico", required=True)

    role = forms.ChoiceField(
        choices=Role.choices,
        label="Rol de Usuario",
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    is_active = forms.BooleanField(
        label="Cuenta Activa",
        required=False,
        help_text="Desmarca esto para bloquear el acceso al usuario sin borrarlo.",
    )

    photo = forms.ImageField(
        label="Foto de perfil", required=False, widget=forms.FileInput
    )
    remove_photo = forms.BooleanField(required=False, label="Eliminar foto actual")

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email", "role", "is_active", "photo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance or not self.instance.photo:
            self.fields["remove_photo"].widget = forms.HiddenInput()

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data.get("remove_photo") and not self.files.get("photo"):
            try:
                if user.photo:
                    user.photo.delete(save=False)
            except Exception:
                pass
            user.photo = None

        if commit:
            user.save()
        return user
