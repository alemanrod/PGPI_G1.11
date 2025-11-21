# order/urls.py
from django.urls import path

import order.views as views

urlpatterns = [
    path("create_checkout/", views.create_checkout, name="create_checkout"),
    path("success/", views.successful_payment, name="successful_payment"),
    path("cancelled/", views.cancelled_payment, name="cancelled_payment"),
    path(
        "track/<str:tracking_code>/",
        views.OrderTrackingView.as_view(),
        name="order_tracking",
    ),
    path("list/", views.OrderListAdminView.as_view(), name="order_list_admin"),
    path("my-orders/", views.OrderListUserView.as_view(), name="order_list_user"),
    path("search/", views.OrderTrackView.as_view(), name="order_search"),
]
