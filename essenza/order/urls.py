# order/urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("create_checkout/", views.create_checkout, name="create_checkout"),
    path("success/", views.successful_payment, name="successful_payment"),
    path("cancelled/", views.cancelled_payment, name="cancelled_payment"),
]
