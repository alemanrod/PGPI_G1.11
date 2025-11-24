# essenza/info/views.py

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import F, Sum
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from order.models import Order, OrderProduct


def info_view(request):
    return render(request, "info/info.html")


class SalesReportsView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Maneja la visualización de los tres tipos de reportes:
    history (Historial de Pedidos), product (Ventas por Producto), user (Ventas por Usuario).
    """

    raise_exception = True

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def get(self, request, report_type="history"):
        reports_nav = [
            {
                "id": "history",
                "name": "Historial de Ventas",
                "url": reverse("info:sales_reports_view", args=["history"]),
            },
            {
                "id": "product",
                "name": "Ventas por Producto",
                "url": reverse("info:sales_reports_view", args=["product"]),
            },
            {
                "id": "user",
                "name": "Ventas por Usuario",
                "url": reverse("info:sales_reports_view", args=["user"]),
            },
        ]

        context = {
            "reports_nav": reports_nav,
            "current_report": report_type,
        }

        if report_type == "product":
            context["report_title"] = "Ventas Totales por Producto"
            context["template_name"] = "info/product_sales.html"
            context["sales_data"] = (
                OrderProduct.objects.values("product__id", "product__name")
                .annotate(
                    total_sold=Sum("quantity"),
                    total_revenue=Sum(F("quantity") * F("product__price")),
                )
                .order_by("-total_revenue")
            )

        elif report_type == "user":
            context["report_title"] = "Ventas Totales por Usuario"
            context["template_name"] = "info/user_sales.html"
            context["sales_data"] = (
                Order.objects.values("user__id", "user__first_name", "user__email")
                .annotate(
                    total_spent=Sum(
                        F("order_products__quantity")
                        * F("order_products__product__price")
                    )
                )
                .exclude(user__isnull=True)
                .order_by("-total_spent")
            )

        else:
            context["report_title"] = "Historial Completo de Ventas"
            context["template_name"] = "info/sales_history.html"
            context["orders"] = Order.objects.all().order_by("-placed_at")

        return render(request, "info/reports_master.html", context)
