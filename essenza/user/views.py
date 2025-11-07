from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login, logout
from .forms import LoginForm


class LoginView(View):
    form_class = LoginForm
    template_name = 'user/login.html'

    def get(self, request, *args, **kwargs):
        # Si el usuario ya está autenticado, lo mandamos a escaparate
        logout(request)
        if request.user.is_authenticated:
            return redirect('escaparate')
        # Si no está autenticado, renderiza el formulario de login
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # Autenticamos al usuario
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                # Redirige al escaparate después del login
                return redirect('escaparate')
            else:
                # Si falla el login, muestra error en el formulario
                form.add_error(None, "Usuario o contraseña incorrectos")

        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    """Cierra la sesión y borra la cookie de sesión."""

    def get(self, request):
        logout(request)
        response = redirect('home')
        # 🔥 borra cookie de sesión en el navegador
        response.delete_cookie('sessionid')
        return response

    def post(self, request):
        logout(request)
        response = redirect('home')
        response.delete_cookie('sessionid')
        return response