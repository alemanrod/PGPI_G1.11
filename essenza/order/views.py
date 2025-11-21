from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.shortcuts import render, redirect
from django.db.models import Prefetch
from .models import Order, OrderProduct, Status

# =======================================================
# LISTADO DE PEDIDOS - ADMIN
# =======================================================
class OrderListAdminView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = "order/order_list_admin.html"

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect("login")
        return redirect("dashboard")

    def get(self, request):
        orders = (
            Order.objects.select_related("user")
            .prefetch_related(
                Prefetch("order_products", queryset=OrderProduct.objects.select_related("product"))
            )
            .order_by("-placed_at")
        )
        return render(request, self.template_name, {"orders": orders})


# =======================================================
# LISTADO DE PEDIDOS - USER
# =======================================================
class OrderListUserView(LoginRequiredMixin, View):
    template_name = "order/order_list_user.html"

    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .exclude(status=Status.EN_PREPARACION)  # carrito / en preparación NO
            .prefetch_related(
                Prefetch("order_products", queryset=OrderProduct.objects.select_related("product"))
            )
            .order_by("-placed_at")
        )
        return render(request, self.template_name, {"orders": orders})


# =======================================================
# SEGUIMIENTO SIN LOGIN
# =======================================================
class OrderTrackView(View):
    template_name = "order/order_track.html"

    def get(self, request):
        # Solo formulario
        return render(request, self.template_name, {"order": None, "searched": False})

    def post(self, request):
        order_id = request.POST.get("order_id", "").strip()
        email = request.POST.get("email", "").strip().lower()

        order = None
        error = None

        if not order_id or not email:
            error = "Debes introducir el número de pedido y el email."
        else:
            try:
                order_pk = int(order_id)
                order = (
                    Order.objects.select_related("user")
                    .prefetch_related(
                        Prefetch("order_products", queryset=OrderProduct.objects.select_related("product"))
                    )
                    .get(pk=order_pk, user__email__iexact=email)
                )
            except (ValueError, Order.DoesNotExist):
                error = "No se ha encontrado ningún pedido con esos datos."

        return render(
            request,
            self.template_name,
            {"order": order, "searched": True, "error": error},
        )
