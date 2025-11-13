from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.views import View

from .models import Product


class DashboardView(View):
    def get(self, request):
        return render(request, "product/dashboard.html")


class StockView(LoginRequiredMixin, UserPassesTestMixin, View):
    # Solo los administradores pueden acceder a esta vista
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == "admin"

    # Solo se ejecutan métodos GET y POST si el usuario pasa la prueba
    def get(self, request):
        # Carga y muestra todos los productos ordenados por nombre
        products = Product.objects.all().order_by("name")
        return render(request, "product/stock.html", {"products": products})

    def post(self, request):
        # Coge datos del formulario para actualizar stock
        product_id = request.POST.get("product_id")
        stock = request.POST.get("stock")

        # Encuentra el producto por su ID
        product = Product.objects.get(pk=product_id)
        if not product:
            messages.error(request, "Producto no encontrado.")
            return redirect("stock")

        # Actualiza el stock del producto
        new_stock = int(stock or 0)
        product.stock = new_stock
        product.save(update_fields=["stock"])
        messages.success(
            request, f"Stock de '{product.name}' actualizado a {new_stock}."
        )

        # Recarga la misma página
        return redirect("stock")
