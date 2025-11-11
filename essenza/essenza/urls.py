from django.contrib import admin
from django.urls import path, include
from info.views import info_view
from product.views import DashboardView

urlpatterns = [
    path('info/', info_view, name='info-home'),
    path("user/", include("user.urls")), 
    path('admin/', admin.site.urls),
    path('', DashboardView.as_view(), name='dashboard')
]