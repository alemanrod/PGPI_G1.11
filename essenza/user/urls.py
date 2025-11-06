from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponse
import user.views as views


urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
]

