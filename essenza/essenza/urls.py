from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponse

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
            </style>
        </head>
        <body>
            <h1>Bienvenidos a Essenza</h1>
            <p>Tu espacio online de cosmética natural, belleza y cuidado personal.</p>
            <p>Explora nuestros productos, descubre nuevas fragancias y disfruta de la experiencia Essenza 🌸</p>
        </body>
    </html>
    """
    return HttpResponse(html)

urlpatterns = [
    path('', home, name='home'),
    path('user/', include('user.urls')),
    path('admin/', admin.site.urls),
]

