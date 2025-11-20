# order/urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("", views.CartDetailView.as_view(), name="order_home"),
    path("cart/", views.CartDetailView.as_view(), name="cart_detail"),
    path("add/<int:product_pk>/", views.AddToCartView.as_view(), name="add_to_cart"),
    path(
        "update/<int:item_pk>/",
        views.UpdateCartItemView.as_view(),
        name="update_cart_item",
    ),
    path(
        "update/session/<int:product_pk>/",
        views.UpdateCartSessionView.as_view(),
        name="update_cart_session",
    ),
    path("create_checkout/", views.create_checkout, name="create_checkout"),
    path("success/", views.successful_payment, name="successful_payment"),
    path("cancelled/", views.cancelled_payment, name="cancelled_payment"),
]
