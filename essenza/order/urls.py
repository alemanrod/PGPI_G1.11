from django.urls import path
from .views import (
    OrderListAdminView,
    OrderListUserView,
    OrderTrackView,
    OrderDetailView,
)

urlpatterns = [
    path("admin/listado/", OrderListAdminView.as_view(), name="order_list_admin"),
    path("mis-pedidos/", OrderListUserView.as_view(), name="order_list_user"),
    path("seguimiento/", OrderTrackView.as_view(), name="order_track"),
    path("pedido/<int:pk>/", OrderDetailView.as_view(), name="order_detail"),

]

