# order/urls.py
from django.urls import path

from . import views

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
    path("history/", views.OrderHistoryView.as_view(), name="order_history"),
    path("search/", views.OrderSearchView.as_view(), name="order_search"),
    path(
        "update-status/<str:tracking_code>/",
        views.OrderUpdateStatusView.as_view(),
        name="order_update_status",
    ),
    path("test-email/", views.test_email_view, name="test_email"),
]
