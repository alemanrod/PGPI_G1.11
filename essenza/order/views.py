from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.shortcuts import render, redirect
from django.db.models import Prefetch
from .models import Order, OrderProduct, Status
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import reverse



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
        # Solo muestra el formulario vacío
        return render(request, self.template_name, {"searched": False})

    def post(self, request):
        order_id = request.POST.get("order_id", "").strip()
        email = request.POST.get("email", "").strip().lower()

        if not order_id or not email:
            return render(
                request,
                self.template_name,
                {
                    "searched": True,
                    "error": "Debes introducir el número de pedido y el email.",
                },
            )

        try:
            order_pk = int(order_id)
            order = (
                Order.objects
                .select_related("user")
                .prefetch_related(
                    Prefetch("order_products", queryset=OrderProduct.objects.select_related("product"))
                )
                .get(pk=order_pk, user__email__iexact=email)
            )
        except (ValueError, Order.DoesNotExist):
            return render(
                request,
                self.template_name,
                {
                    "searched": True,
                    "error": "No se ha encontrado ningún pedido con esos datos.",
                },
            )

        return redirect(f"{reverse('order_detail', kwargs={'pk': order.pk})}?from=track")



class OrderDetailView(View):
    template_name = "order/order_detail.html"

    def get(self, request, pk):
        order = (
            Order.objects
            .select_related("user")
            .prefetch_related(
                Prefetch("order_products", queryset=OrderProduct.objects.select_related("product"))
            )
            .filter(pk=pk)
            .first()
        )

        if not order:
            raise Http404("Pedido no encontrado")

        # ✅ Permitir anónimos SOLO si vienen del seguimiento
        if not request.user.is_authenticated:
            if request.GET.get("from") == "track":
                return render(request, self.template_name, {"order": order})
            return redirect("login")

        # 🛡 Permisos normales
        if request.user.role != "admin" and order.user != request.user:
            raise PermissionDenied

        return render(request, self.template_name, {"order": order})
