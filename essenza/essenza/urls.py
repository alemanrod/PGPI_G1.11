from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from info import views

def home(request):
    html = """
    <html>
        <head>
            <title>Essenza</title>
            <style>
                body {
                    background-color: #faf7f2;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    text-align: center;
                    padding-top: 100px;
                    color: #444;
                    position: relative;
                }
                h1 {
                    color: #c06b3e;
                    font-size: 48px;
                    margin-bottom: 10px;
                }
                p {
                    font-size: 20px;
                    color: #555;
                }
                .info-button {
                    position: absolute;
                    top: 20px;
                    left: 20px;
                    width: 30px;
                    height: 30px;
                    background-color: #c06b3e;
                    border-radius: 50%;
                    text-align: center;
                    line-height: 30px;
                    font-size: 18px;
                    font-weight: bold;
                    color: white;
                    text-decoration: none;
                    cursor: pointer;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    transition: background-color 0.3s;
                }
                .info-button:hover { background-color: #a35a34; }
                .login-button {
                    position: absolute;
                    top: 60%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    padding: 15px 35px;
                    background-color: #c06b3e;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border: none;
                    border-radius: 10px;
                    cursor: pointer;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    text-decoration: none;
                    transition: background-color 0.3s, transform 0.2s;
                }
                .login-button:hover {
                    background-color: #a35a34;
                    transform: translate(-50%, -50%) scale(1.05);
                }
            </style>
        </head>
        <body>
            <a href="/info/" class="info-button" title="Información Legal y Contacto">i</a>
            <h1>Bienvenidos a Essenza</h1>
            <p>Tu espacio online de cosmética natural, belleza y cuidado personal.</p>
            <p>Explora nuestros productos, descubre nuevas fragancias y disfruta de la experiencia Essenza 🌸</p>

            <a href="/user/login" class="login-button" title="Iniciar Sesión">Iniciar sesión</a>
        </body>
    </html>
    """
    return HttpResponse(html)

urlpatterns = [
    path('', home, name='home'),
    path('info/', views.info_view, name='info-home'),
    path("user/", include("user.urls")), 
    path('user/login/', include('user.urls')),
    path("accounts/", include("django.contrib.auth.urls")), 
    path('admin/', admin.site.urls)
]

