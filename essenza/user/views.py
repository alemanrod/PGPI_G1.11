# Create your views here.
from django.shortcuts import render, redirect
from django.views import View
from .forms import RegisterForm
import templates

class RegisterView(View):
    """
    Controla el registro de usuarios.
    """
    form_class = RegisterForm
    # El archivo HTML que debe renderizar esta vista
    template_name = 'user/register.html' 

    def get(self, request, *args, **kwargs):
        # Muestra el formulario vacío
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES) 
        
        if form.is_valid():
            user = form.save() # Guarda el nuevo usuario en la BBDD
            
            # Redirige a la página principal (definida como 'home' en info/urls.py)
            return redirect('home') 

        return render(request, self.template_name, {'form': form})