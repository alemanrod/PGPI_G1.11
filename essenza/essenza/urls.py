from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from info.views import info_view
from product.views import EscaparateView
import user

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
                
                .button-container {
                    margin-top: 30px; /* Espacio desde el texto de arriba */
                    display: flex;
                    flex-direction: column; /* Apila los botones verticalmente */
                    align-items: center;  /* Centra los botones horizontalmente */
                    gap: 20px; /* Espacio automático entre cada botón */
                }

                .action-button {
                    padding: 15px 35px;
                    background-color: #c06b3e;
                    color: white;
                    font-size: 15px;
                    font-weight: bold;
                    border: none;
                    border-radius: 10px;
                    cursor: pointer;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    text-decoration: none;
                    transition: background-color 0.3s, transform 0.2s;
                    
                    display: block;
                    width: 300px; /* Ancho fijo para que se vean uniformes */
                    box-sizing: border-box; /* Para que el padding no afecte el ancho */
                }
                
                .action-button:hover {
                    background-color: #a35a34;
                    transform: scale(1.05); /* Efecto de zoom simple */
                }
                
            </style>
        </head>
        <body>
            <a href="/info/" class="info-button" title="Información Legal y Contacto">i</a>
            <h1>Bienvenidos a Essenza</h1>
            <p>Tu espacio online de cosmética natural, belleza y cuidado personal.</p>
            <p>Explora nuestros productos, descubre nuevas fragancias y disfruta de la experiencia Essenza 🌸</p>

            <div class="button-container">
                <a href="/user/register" class="action-button" title="Registro">Registro</a>
                <a href="/user/login" class="action-button" title="Iniciar Sesión">Iniciar sesión</a>
                <a href="/escaparate" class="action-button" title="invitado">Continuar como invitado</a>
            </div>
        </body>
    </html>
    """
    return HttpResponse(html)

urlpatterns = [
    path('', home, name='home'),
    path('info/', info_view, name='info-home'),
    path("user/", include("user.urls")), 
    path('admin/', admin.site.urls),
    path('escaparate/', EscaparateView.as_view(), name='escaparate')
]