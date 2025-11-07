from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login

from essenza.urls import home
from .forms import LoginForm


class LoginView(View):
    form_class = LoginForm
    template_name = 'user/login.html'
    

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
           return redirect('home')
        return render(request, self.template_name, {'form': self.form_class()})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                form.add_error(None, "Usuario o contraseña incorrectos")

        return render(request, self.template_name, {'form': form})

