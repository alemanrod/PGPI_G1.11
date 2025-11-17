from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin  # Para proteger vistas
from django.shortcuts import redirect, render
from django.views import View

from .forms import LoginForm, ProfileEditForm, RegisterForm


class LoginView(View):
    form_class = LoginForm
    template_name = "user/login.html"

    def get(self, request, *args, **kwargs):
        # Si el usuario ya está autenticado, lo mandamos a dashboard
        if request.user.is_authenticated:
            return redirect("dashboard")
        # Si no está autenticado, renderiza el formulario de login
        return render(request, self.template_name, {"form": self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # Autenticamos al usuario
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                if user.role == "user":
                    return redirect("dashboard")
                else:
                    return redirect("stock")
            else:
                # Si falla el login, muestra error en el formulario
                form.add_error(None, "Usuario o contraseña incorrectos")

        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def get(self, request):
        logout(request)
        response = redirect("dashboard")
        response.delete_cookie("sessionid")
        return response

    def post(self, request):
        logout(request)
        response = redirect("dashboard")
        response.delete_cookie("sessionid")
        return response


class RegisterView(View):
    form_class = RegisterForm
    template_name = "user/register.html"

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")

        return render(request, self.template_name, {"form": form})


class ProfileView(LoginRequiredMixin, View):
    template_name = "user/profile.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)


class ProfileEditView(LoginRequiredMixin, View):
    form_class = ProfileEditForm
    template_name = "user/edit_profile.html"

    def get(self, request, *args, **kwargs):
        # Rellena el formulario con los datos actuales del usuario
        form = self.form_class(instance=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        # Guarda la foto antigua para borrarla si se ha cambiado
        try:
            old_photo = request.user.photo
        except AttributeError:
            old_photo = None

        # Rellena el formulario con los datos enviados
        form = self.form_class(request.POST, request.FILES, instance=request.user)

        # Si el formulario es válido, se redirige a la vista de perfil
        if form.is_valid():
            new_user = form.save()
            # Si había una foto antigua y es distinta a la nueva, la borramos del sistema
            if old_photo and old_photo != new_user.photo:
                old_photo.delete(save=False)
            return redirect("profile")

        # Si el formulario no es válido, se vuelve a mostrar con errores
        return render(request, self.template_name, {"form": form})


class ProfileDeleteView(LoginRequiredMixin, View):
    template_name = "user/confirm_delete_profile.html"

    def get(self, request, *args, **kwargs):
        # Muestra la página de confirmación
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # Guarda la foto antigua para borrarla
        try:
            photo_to_delete = request.user.photo
        except AttributeError:
            photo_to_delete = None
        user = request.user

        # Cierra la sesión ANTES de borrar al usuario para evitar errores
        logout(request)
        # Borra el usuario de la base de datos
        user.delete()
        # Borra, si la hay, la foto del sistema de archivos
        if photo_to_delete:
            photo_to_delete.delete(save=False)

        return redirect("dashboard")
