from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import (  # Para proteger vistas
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import (
    LoginForm,
    ProfileEditForm,
    RegisterForm,
    UserCreationFormAdmin,
    UserEditFormAdmin,
)
from .models import Usuario


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


class UserListView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "user/user_list.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect("login")
        return redirect("dashboard")

    def get(self, request):
        role_filter = request.GET.get("role", "all")
        order_filter = request.GET.get("order", "newest")
        users = Usuario.objects.all()
        # Filtrado por rol
        if role_filter == "admin":
            users = users.filter(role="admin")
        elif role_filter == "user":
            users = users.filter(role="user")
        # Ordenación
        if order_filter == "oldest":
            users = users.order_by("date_joined")
        elif order_filter == "name_asc":
            users = users.order_by("first_name", "username")
        elif order_filter == "name_desc":
            users = users.order_by("-first_name", "-username")
        elif order_filter == "email_asc":
            users = users.order_by("email")
        elif order_filter == "email_desc":
            users = users.order_by("-email")
        elif order_filter == "login_desc":
            users = users.order_by(F("last_login").desc(nulls_last=True))
        elif order_filter == "login_asc":
            users = users.order_by(F("last_login").asc(nulls_first=True))
        else:
            users = users.order_by("-date_joined")
        return render(request, self.template_name, {"users": users})


class UserCreateViewAdmin(LoginRequiredMixin, UserPassesTestMixin, View):
    form_class = UserCreationFormAdmin
    template_name = "user/user_create_admin.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        return redirect("dashboard")

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)

        if form.is_valid():
            form.save()

            return redirect("user_list")

        return render(request, self.template_name, {"form": form})


class UserUpdateViewAdmin(LoginRequiredMixin, UserPassesTestMixin, View):
    form_class = UserEditFormAdmin
    template_name = "user/user_edit_admin.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        return redirect("dashboard")

    def get(self, request, pk, *args, **kwargs):
        user_to_edit = get_object_or_404(Usuario, pk=pk)

        form = self.form_class(instance=user_to_edit)
        return render(request, self.template_name, {"form": form})

    def post(self, request, pk, *args, **kwargs):
        user_to_edit = get_object_or_404(Usuario, pk=pk)

        try:
            old_photo = user_to_edit.photo
        except AttributeError:
            old_photo = None

        form = self.form_class(request.POST, request.FILES, instance=user_to_edit)

        if form.is_valid():
            saved_user = form.save()

            if old_photo and old_photo != saved_user.photo:
                try:
                    old_photo.delete(save=False)
                except Exception:
                    pass

            return redirect("user_list")

        return render(request, self.template_name, {"form": form})


class UserDeleteViewAdmin(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "user/confirm_delete_user_admin.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        return redirect("dashboard")

    def get(self, request, pk, *args, **kwargs):
        user_to_delete = get_object_or_404(Usuario, pk=pk)

        if user_to_delete == request.user:
            return redirect("user_list")

        return render(request, self.template_name, {"object": user_to_delete})

    def post(self, request, pk, *args, **kwargs):
        user_to_delete = get_object_or_404(Usuario, pk=pk)

        if user_to_delete == request.user:
            return redirect("user_list")

        try:
            photo_to_delete = user_to_delete.photo
        except AttributeError:
            photo_to_delete = None

        user_to_delete.delete()

        if photo_to_delete:
            try:
                photo_to_delete.delete(save=False)
            except Exception:
                pass

        return redirect("user_list")
