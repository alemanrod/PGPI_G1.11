from django.urls import path

from .views import AddToCartView, CartDetailView, RemoveFromCartView, UpdateCartItemView

urlpatterns = [
    path("", CartDetailView.as_view(), name="cart_detail"),
    path("add/<int:product_id>/", AddToCartView.as_view(), name="add_to_cart"),
    path(
        "update/<int:product_id>/",
        UpdateCartItemView.as_view(),
        name="update_cart_item",
    ),
    path(
        "remove/<int:product_id>/",
        RemoveFromCartView.as_view(),
        name="remove_from_cart",
    ),
]
