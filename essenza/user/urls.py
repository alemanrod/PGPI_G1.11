from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponse
from user import views

app_name = "user"

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

]

