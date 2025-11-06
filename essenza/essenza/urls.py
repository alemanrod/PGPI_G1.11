from django.contrib import admin
from django.urls import path
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
                    /* Aseguramos que el cuerpo permita posicionamiento absoluto para el botón */
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
                /* Estilo para el botón de Información (simulando la 'i' del mockup) */
                .info-button {
                    position: absolute;
                    top: 20px; /* Distancia desde la parte superior */
                    left: 20px; /* Distancia desde la izquierda */
                    width: 30px;
                    height: 30px;
                    background-color: #c06b3e; /* Color corporativo o distintivo */
                    border-radius: 50%; /* Forma circular */
                    text-align: center;
                    line-height: 30px; /* Centra verticalmente la 'i' */
                    font-size: 18px;
                    font-weight: bold;
                    color: white;
                    text-decoration: none; /* Elimina el subrayado del enlace */
                    cursor: pointer;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    transition: background-color 0.3s;
                }
                .info-button:hover {
                    background-color: #a35a34; /* Oscurece al pasar el ratón */
                }
            </style>
        </head>
        <body>
            <a href="/info/" class="info-button" title="Información Legal y Contacto">i</a>
            
            <h1>Bienvenidos a Essenza</h1>
            <p>Tu espacio online de cosmética natural, belleza y cuidado personal.</p>
            <p>Explora nuestros productos, descubre nuevas fragancias y disfruta de la experiencia Essenza 🌸</p>
        </body>
    </html>
    """
    return HttpResponse(html)

urlpatterns = [
    path('', home, name='home'),
    path('info/', views.info_view, name='info-home'),
    path('admin/', admin.site.urls),
]

