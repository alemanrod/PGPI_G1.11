# essenza/info/urls.py

from django.urls import path

from . import views

urlpatterns = [
    path("", views.info_view, name="info-home"),
    path(
        "reports/",
        views.SalesReportsView.as_view(),
        {"report_type": "history"},
        name="sales_history_report",
    ),
    path(
        "reports/<str:report_type>/",
        views.SalesReportsView.as_view(),
        name="sales_reports_view",
    ),
]
