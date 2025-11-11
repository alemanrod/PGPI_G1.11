# views.py (donde se encuentra la función info_view)

from django.shortcuts import render

def info_view(request):
    return render(request, "info/info.html")